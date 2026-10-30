import logging
import time
import uuid

from flask import Flask, g, request
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from config import Config
from app.celery_app import init_celery
from app.openapi import register_openapi_routes
from app.errors import register_error_handlers

db = SQLAlchemy()
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
    CORS(app, resources={r"/api/*": {"origins": app.config.get("CORS_ORIGINS", "*")}})

    # 统一 JSON 错误处理（所有错误都返回结构化 JSON）
    register_error_handlers(app)

    # 请求日志中间件（生成 request_id、记录耗时与状态）
    _register_request_logging(app)

    # 初始化 Celery 异步任务（把任务绑定到本应用的应用上下文）
    init_celery(app)

    # 注册 API 蓝图（在 create_app 内部导入，避免循环导入）
    from app.api.auth import auth_bp
    from app.api.posts import posts_bp
    from app.api.categories import categories_bp
    from app.api.favorites import favorites_bp
    from app.api.admin import admin_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(posts_bp, url_prefix='/api/posts')
    app.register_blueprint(categories_bp, url_prefix='/api/categories')
    app.register_blueprint(favorites_bp, url_prefix='/api/favorites')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')

    # 注册 OpenAPI 规范与 Swagger UI 文档路由
    register_openapi_routes(app)

    return app


def _configure_logging(app):
    """统一日志格式：时间 级别 模块: 消息。"""
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s %(name)s: %(message)s'
    ))
    app.logger.handlers = [handler]
    app.logger.setLevel(logging.INFO)


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