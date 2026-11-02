import os

from dotenv import load_dotenv
from sqlalchemy.pool import StaticPool

# 从 .env 文件加载环境变量（仅开发环境使用）
load_dotenv()


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///blog.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # ---------- 连接池调优（MySQL 生效，SQLite 忽略） ----------
    # pool_pre_ping：取连接前先 ping，自动丢弃 MySQL 主动断开的陈旧连接，避免 500 Broken pipe
    # pool_size / max_overflow：连接池基础大小 + 溢出上限（并发峰值可临时多开）
    # pool_recycle：连接最长存活时间，避免超过 MySQL wait_timeout 被服务端回收
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_size': int(os.environ.get('DB_POOL_SIZE', 5)),
        'max_overflow': int(os.environ.get('DB_MAX_OVERFLOW', 10)),
        'pool_recycle': int(os.environ.get('DB_POOL_RECYCLE', 1800)),
        'pool_timeout': int(os.environ.get('DB_POOL_TIMEOUT', 10)),
    }

    # ---------- 慢查询日志 ----------
    # 单条 SQL 执行超过该毫秒数时记录 WARNING，便于定位慢查询（对应知识域：慢查询分析）
    SLOW_QUERY_MS = int(os.environ.get('SLOW_QUERY_MS', 200))

    # JWT 认证配置
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'dev-jwt-secret-key-please-change-0123456789abcdef')
    JWT_ACCESS_TOKEN_EXPIRES = int(os.environ.get('JWT_EXPIRES', 900))        # 秒：access token 15 分钟
    JWT_REFRESH_TOKEN_EXPIRES = int(os.environ.get('JWT_REFRESH_EXPIRES', 604800))  # 秒：refresh token 7 天
    JWT_TOKEN_LOCATION = ['headers']
    JWT_HEADER_NAME = 'Authorization'
    JWT_HEADER_TYPE = 'Bearer'
    # 允许跨域的来源（Vue 开发服务器）
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', 'http://localhost:5173')

    # ---------- Redis 缓存 ----------
    # 缓存是可降级的加速层：Redis 未配置或连不上时，直接放行原逻辑，不影响业务
    CACHE_ENABLED = os.environ.get('CACHE_ENABLED', 'true').lower() in ('1', 'true', 'yes', 'on')
    CACHE_REDIS_URL = os.environ.get('CACHE_REDIS_URL', 'redis://localhost:6379/0')
    CACHE_DEFAULT_TIMEOUT = int(os.environ.get('CACHE_DEFAULT_TIMEOUT', 60))

    # ---------- Celery 异步任务 ----------
    CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/1')
    CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/1')
    # 测试环境可开启 eager：让 .delay() 同步执行，不真正发到 broker
    CELERY_TASK_ALWAYS_EAGER = os.environ.get(
        'CELERY_TASK_ALWAYS_EAGER', 'false').lower() in ('1', 'true', 'yes', 'on')
    CELERY_TASK_EAGER_PROPAGATES = os.environ.get(
        'CELERY_TASK_EAGER_PROPAGATES', 'false').lower() in ('1', 'true', 'yes', 'on')
    # ---------- 安全纵深 ----------
    # 统一安全响应头开关（生产开启；测试可关避免断言干扰）
    SECURITY_HEADERS_ENABLED = os.environ.get(
        'SECURITY_HEADERS_ENABLED', 'true').lower() in ('1', 'true', 'yes', 'on')

    # ---------- 登录保护 ----------
    # 连续登录失败达到阈值后锁定该账号一段时间（防暴力破解）
    LOGIN_MAX_FAILURES = int(os.environ.get('LOGIN_MAX_FAILURES', 5))
    LOGIN_LOCKOUT_SECONDS = int(os.environ.get('LOGIN_LOCKOUT_SECONDS', 300))

    # ---------- 可观测性指标 ----------
    # Prometheus 指标端点 /metrics 开关（生产/开发默认开，测试关）
    METRICS_ENABLED = os.environ.get('METRICS_ENABLED', 'true').lower() in ('1', 'true', 'yes', 'on')

    # ---------- 限流防刷 ----------
    RATELIMIT_ENABLED = os.environ.get('RATELIMIT_ENABLED', 'true').lower() in ('1', 'true', 'yes', 'on')
    # 限流存储默认用进程内内存（开发/单机安全）；生产多实例可覆盖为 redis:// 实现共享限流
    RATELIMIT_STORAGE_URI = os.environ.get('RATELIMIT_STORAGE_URI', 'memory://')


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    # 测试专用配置：内存 SQLite + eager 同步任务 + 关闭缓存/限流
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite://'
    SQLALCHEMY_ENGINE_OPTIONS = {
        'poolclass': StaticPool,
        'connect_args': {'check_same_thread': False},
    }
    SECRET_KEY = 'test-secret-key-0123456789abcdef'
    JWT_SECRET_KEY = 'test-jwt-secret-key-0123456789abcdef'
    JWT_ACCESS_TOKEN_EXPIRES = 3600
    CORS_ORIGINS = '*'
    CACHE_ENABLED = False
    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_TASK_EAGER_PROPAGATES = True
    CELERY_BROKER_URL = 'memory://'
    CELERY_RESULT_BACKEND = 'cache+memory://'
    RATELIMIT_ENABLED = False
    SECURITY_HEADERS_ENABLED = False
    METRICS_ENABLED = False


class ProductionConfig(Config):
    DEBUG = False


# 根据环境变量选择配置；显式传入配置类优先级最高
config_map = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig,
}


def get_config(env=None):
    # 按环境名取配置类。优先级：显式参数 > FLASK_ENV 环境变量 > 默认开发
    import os
    if env is None:
        env = os.environ.get('FLASK_ENV', 'development')
    return config_map.get(env, config_map['default'])
