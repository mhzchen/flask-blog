import logging
import time
import uuid

from flask import Flask, g, request, jsonify
from sqlalchemy import event
from sqlalchemy.engine import Engine
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from config import Config
from app.celery_app import init_celery
from app.openapi import register_openapi_routes
from app.errors import register_error_handlers
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

db = SQLAlchemy()
limiter = Limiter(key_func=get_remote_address)
migrate = Migrate()
jwt = JWTManager()


def create_app(config_class=Config):
    """应用工厂：根据配置类创建 Flask 应用实例"""
    app = Flask(__name__)
    app.config.from_object(config_class)
    _configure_logging(app)

    # 初始化扩展
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    limiter.init_app(app)
    CORS(app, resources={r"/api/*": {"origins": app.config.get("CORS_ORIGINS", "*")}})

    # 统一 JSON 错误处理（所有错误都返回结构化 JSON）
    register_error_handlers(app)

    # 请求日志中间件（生成 request_id、记录耗时与状态）
    _register_request_logging(app)

    # 慢查询日志：单条 SQL 超过阈值自动记录 WARNING
    _register_slow_query_logging(app)

    # 初始化 Celery 异步任务（把任务绑定到本应用的应用上下文）
    init_celery(app)

    # 注册 API 蓝图（在 create_app 内部导入，避免循环导入）
    from app.api.auth import auth_bp
    from app.api.posts import posts_bp
    from app.api.categories import categories_bp
    from app.api.favorites import favorites_bp
    from app.api.admin import admin_bp
    from app.api.comments import comments_bp
    from app.api.tags import tags_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(posts_bp, url_prefix='/api/posts')
    app.register_blueprint(categories_bp, url_prefix='/api/categories')
    app.register_blueprint(favorites_bp, url_prefix='/api/favorites')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    app.register_blueprint(comments_bp, url_prefix='/api')
    app.register_blueprint(tags_bp, url_prefix='/api/tags')

    # 注册 OpenAPI 规范与 Swagger UI 文档路由
    register_openapi_routes(app)

    @app.get('/health')
    def health():
        """存活探针：进程活着即返回 ok（不含依赖检查，供负载均衡初判）。"""
        return {'status': 'ok'}

    @app.get('/healthz')
    def healthz():
        """就绪探针：检查数据库连通性，供 Docker/K8s 判断是否可承接流量。"""
        checks = {}
        ok = True
        # 数据库检查
        try:
            db.session.execute(db.text('SELECT 1'))
            checks['database'] = 'ok'
        except Exception as e:  # noqa: BLE001
            ok = False
            checks['database'] = f'error: {e}'
        status = 'ok' if ok else 'error'
        return jsonify({'status': status, 'checks': checks}), 200 if ok else 503

    return app


def _configure_logging(app):
    """统一日志格式：时间 级别 模块: 消息。"""
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s %(name)s: %(message)s'
    ))
    app.logger.handlers = [handler]
    app.logger.setLevel(logging.INFO)


def _register_slow_query_logging(app):
    """慢查询日志：统计每条 SQL 执行耗时，超过阈值记录 WARNING。"""
    threshold_ms = app.config.get('SLOW_QUERY_MS', 200)

    @event.listens_for(Engine, 'before_cursor_execute')
    def _before(conn, cursor, statement, parameters, context, executemany):
        conn.info.setdefault('_slow_start', time.perf_counter())

    @event.listens_for(Engine, 'after_cursor_execute')
    def _after(conn, cursor, statement, parameters, context, executemany):
        started = conn.info.pop('_slow_start', None)
        if started is None:
            return
        dur_ms = (time.perf_counter() - started) * 1000
        if dur_ms >= threshold_ms:
            sql = statement.splitlines()[0][:200] if statement else ''
            app.logger.warning(
                'slow_query dur_ms=%.1f sql=%s', dur_ms, sql,
            )


def _register_request_logging(app):
    """为每个请求生成 request_id，并在响应后记录一行结构化日志。"""

    @app.before_request
    def _start_timer():
        g.request_id = uuid.uuid4().hex[:12]
        g._start_time = time.perf_counter()

    @app.after_request
    def _log_request(resp):
        duration_ms = (time.perf_counter() - getattr(g, '_start_time', time.perf_counter())) * 1000
        req_id = getattr(g, 'request_id', '-')
        resp.headers['X-Request-Id'] = req_id
        app.logger.info(
            'req method=%s path=%s status=%s dur_ms=%.1f rid=%s ip=%s',
            request.method, request.path, resp.status_code, duration_ms, req_id,
            request.remote_addr,
        )
        return resp