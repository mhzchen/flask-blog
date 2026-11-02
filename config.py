import os
from dotenv import load_dotenv

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
    CELERY_TASK_ALWAYS_EAGER = os.environ.get('CELERY_TASK_ALWAYS_EAGER', 'false').lower() in ('1', 'true', 'yes', 'on')
    CELERY_TASK_EAGER_PROPAGATES = os.environ.get('CELERY_TASK_EAGER_PROPAGATES', 'false').lower() in ('1', 'true', 'yes', 'on')
    # ---------- 限流防刷 ----------
    RATELIMIT_ENABLED = os.environ.get('RATELIMIT_ENABLED', 'true').lower() in ('1', 'true', 'yes', 'on')
    # 限流存储默认用进程内内存（开发/单机安全）；生产多实例可覆盖为 redis:// 实现共享限流
    RATELIMIT_STORAGE_URI = os.environ.get('RATELIMIT_STORAGE_URI', 'memory://')


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


# 根据环境变量选择配置
config_map = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig,
}