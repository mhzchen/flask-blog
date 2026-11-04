"""限流深化测试（#61）：Redis 限流存储不可达时的内存降级。

计数型限流行为（429 触发 / 配额响应头 / 全局默认限流 / 分布式共享）由真实 HTTP
真验脚本覆盖——Flask-Limiter 为模块级单例且多 app 顺序复用 storage 会污染计数，
单元测试只保留不依赖计数的降级记录断言。
"""

from app import create_app, db
from sqlalchemy.pool import StaticPool


class _RedisDownConfig:
    """限流存储指向不可达 Redis：验证启动自动降级内存 + 记降级事件。"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite://'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {'poolclass': StaticPool, 'connect_args': {'check_same_thread': False}}
    SECRET_KEY = 'test-rl-secret-key-0123456789abcdef'
    JWT_SECRET_KEY = 'test-rl-jwt-key-0123456789abcdef'
    CACHE_ENABLED = False
    CELERY_TASK_ALWAYS_EAGER = True
    RATELIMIT_ENABLED = True
    RATELIMIT_STORAGE_URI = 'redis://127.0.0.1:6399/4'
    RATELIMIT_DEFAULT_LIMITS = ["200 per minute"]
    RATELIMIT_HEADERS_ENABLED = True


def test_ratelimit_redis_down_fallback():
    """Redis 限流存储不可达 → 探测失败写回 memory config 并记降级事件（运行时请求由真验覆盖）"""
    from app.degradation import degradation_summary
    app = create_app(_RedisDownConfig)
    with app.app_context():
        try:
            assert app.config['RATELIMIT_STORAGE_URI'] == 'memory://'  # 已降级
            services = {d['service'] for d in degradation_summary()}
            assert 'redis_ratelimit' in services
        finally:
            db.session.remove()
            db.drop_all()
