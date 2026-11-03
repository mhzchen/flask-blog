import os

from dotenv import load_dotenv
from sqlalchemy.pool import StaticPool

# 从 .env 文件加载环境变量（仅开发环境使用）
load_dotenv()


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///blog.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # ---------- 读写分离 ----------
    # 配了 DATABASE_URL_SLAVE（从库连接串）则启用多 bind：default=主库（写）、slave=从库（读）。
    # 未配置则回退单库（dev/SQLite/测试不受影响）。从库连接池与主库同一套优化参数。
    _DATABASE_URL_SLAVE = os.environ.get('DATABASE_URL_SLAVE', '')
    SQLALCHEMY_BINDS = {'slave': _DATABASE_URL_SLAVE} if _DATABASE_URL_SLAVE else {}
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
    # ---------- 慢请求采样 ----------
    # 整请求耗时超过该毫秒数时，按采样率额外记录 WARNING（区别于全部请求的 INFO req 行，
    # 用于在生产里精准抓慢请求，且与慢 SQL 一样带上 request_id 可串联排查）
    SLOW_REQUEST_MS = int(os.environ.get('SLOW_REQUEST_MS', 1000))
    # 采样率 0~1：默认全量（1.0）；高流量环境可调低，避免慢请求日志洪峰
    SLOW_REQUEST_SAMPLE_RATE = float(os.environ.get('SLOW_REQUEST_SAMPLE_RATE', 1.0))

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
    # 详情缓存 TTL 基数；防雪崩会在 base ±20% 随机抖动
    CACHE_DETAIL_TIMEOUT = int(os.environ.get('CACHE_DETAIL_TIMEOUT', 60))
    # 防穿透：不存在的资源（如不存在的文章 id）也写短 TTL 空标记缓存
    CACHE_NEGATIVE_TIMEOUT = int(os.environ.get('CACHE_NEGATIVE_TIMEOUT', 30))

    # ---------- Celery 异步任务 ----------
    CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/1')
    CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/1')
    # 测试环境可开启 eager：让 .delay() 同步执行，不真正发到 broker
    CELERY_TASK_ALWAYS_EAGER = os.environ.get(
        'CELERY_TASK_ALWAYS_EAGER', 'false').lower() in ('1', 'true', 'yes', 'on')
    CELERY_TASK_EAGER_PROPAGATES = os.environ.get(
        'CELERY_TASK_EAGER_PROPAGATES', 'false').lower() in ('1', 'true', 'yes', 'on')

    # ---------- 异步任务失败告警 ----------
    # Celery 任务失败时推送到此 webhook（容器内默认指向 backend 自身的 /api/internal/alerts 作为接收端，
    # 便于本地闭环验证；生产可改为真实告警网关 URL——企业微信/钉钉/Slack 机器人）。
    ALERT_WEBHOOK_URL = os.environ.get('ALERT_WEBHOOK_URL', 'http://backend:8000/api/internal/alerts')
    # 周期任务预热缓存时，内部请求 backend 用的基址（容器网络用 backend:8000，本地开发用 localhost:8000）
    BACKEND_INTERNAL_URL = os.environ.get('BACKEND_INTERNAL_URL', 'http://localhost:8000')
    # 死信列表保留的最大条数（周期任务 ltrim 清理，防无限膨胀）
    DEADLETTER_MAX = int(os.environ.get('DEADLETTER_MAX', 100))
    # ---------- 安全纵深 ----------
    # 统一安全响应头开关（生产开启；测试可关避免断言干扰）
    SECURITY_HEADERS_ENABLED = os.environ.get(
        'SECURITY_HEADERS_ENABLED', 'true').lower() in ('1', 'true', 'yes', 'on')

    # ---------- 登录保护 ----------
    # 连续登录失败达到阈值后锁定该账号一段时间（防暴力破解）
    LOGIN_MAX_FAILURES = int(os.environ.get('LOGIN_MAX_FAILURES', 5))
    LOGIN_LOCKOUT_SECONDS = int(os.environ.get('LOGIN_LOCKOUT_SECONDS', 300))
    # 共享锁定开关：开启则失败计数存 Redis（多 worker/多实例共享，锁定才有效）；
    # 关闭或 Redis 不可用时自动降级为进程内 dict（单机也能用，只是多实例下不共享）
    LOGIN_REDIS_ENABLED = os.environ.get(
        'LOGIN_REDIS_ENABLED', 'true').lower() in ('1', 'true', 'yes', 'on')

    # ---------- 可观测性指标 ----------
    # Prometheus 指标端点 /metrics 开关（生产/开发默认开，测试关）
    METRICS_ENABLED = os.environ.get('METRICS_ENABLED', 'true').lower() in ('1', 'true', 'yes', 'on')

    # ---------- OpenTelemetry 全链路追踪 ----------
    # 为真时初始化 OTel，给 Flask/SQLAlchemy/Redis/Celery 装 instrumentation，产生 HTTP->DB->Redis->Celery 一条 trace
    OTEL_ENABLED = os.environ.get('OTEL_ENABLED', 'true').lower() in ('1', 'true', 'yes', 'on')
    # 配了 OTLP endpoint（如 Jaeger/Tempo/Collector）走 OTLP 导出；留空则用 ConsoleSpanExporter 直接输出 stdout
    OTEL_EXPORTER_OTLP_ENDPOINT = os.environ.get('OTEL_EXPORTER_OTLP_ENDPOINT', '')
    OTEL_SERVICE_NAME = os.environ.get('OTEL_SERVICE_NAME', 'flask-blog')
    OTEL_SERVICE_VERSION = os.environ.get('OTEL_SERVICE_VERSION', '1.0.0')


    # ---------- WebSocket 实时推送（生产化） ----------
    # 多 worker / 多实例广播需配 SOCKETIO_MESSAGE_QUEUE（redis 消息队列），Flask-SocketIO
    # 经 redis pub/sub 跨进程广播；未配置则广播只在本进程（单 worker 场景）
    SOCKETIO_MESSAGE_QUEUE = os.environ.get('SOCKETIO_MESSAGE_QUEUE', '')

    # ---------- 服务降级开关（#58） ----------
    # 总开关默认 true=依赖故障时降级继续服务（业务不中断）；false=遇故障 fail-fast 抛错
    SERVICE_DEGRADATION_ENABLED = os.environ.get(
        'SERVICE_DEGRADATION_ENABLED', 'true').lower() in ('1', 'true', 'yes', 'on')
    # 各服务降级开关（可单独关闭；关闭后该服务故障即 fail-fast，不再静默降级）
    DEGRADATION_REDIS_CACHE = os.environ.get('DEGRADATION_REDIS_CACHE', 'true').lower() in ('1', 'true', 'yes', 'on')
    DEGRADATION_REDIS_LOGIN = os.environ.get('DEGRADATION_REDIS_LOGIN', 'true').lower() in ('1', 'true', 'yes', 'on')
    DEGRADATION_REDIS_JWT = os.environ.get('DEGRADATION_REDIS_JWT', 'true').lower() in ('1', 'true', 'yes', 'on')
    DEGRADATION_REDIS_IDEM = os.environ.get('DEGRADATION_REDIS_IDEM', 'true').lower() in ('1', 'true', 'yes', 'on')
    DEGRADATION_MEILISEARCH = os.environ.get('DEGRADATION_MEILISEARCH', 'true').lower() in ('1', 'true', 'yes', 'on')
    DEGRADATION_CELERY = os.environ.get('DEGRADATION_CELERY', 'true').lower() in ('1', 'true', 'yes', 'on')
    DEGRADATION_OTEL = os.environ.get('DEGRADATION_OTEL', 'true').lower() in ('1', 'true', 'yes', 'on')
    DEGRADATION_DBROUTING = os.environ.get('DEGRADATION_DBROUTING', 'true').lower() in ('1', 'true', 'yes', 'on')

    # ---------- 日志聚合（#58）：日志按天滚动落盘，便于集中采集/聚合查看 ----------
    LOG_FILE_ENABLED = os.environ.get('LOG_FILE_ENABLED', 'false').lower() in ('1', 'true', 'yes', 'on')
    LOG_DIR = os.environ.get('LOG_DIR', 'logs')
    LOG_FILE_BACKUP_DAYS = int(os.environ.get('LOG_FILE_BACKUP_DAYS', '14'))

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
    CACHE_REDIS_URL = None  # 测试不连真实 Redis；缓存/登录锁定测试用 FakeRedis 注入
    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_TASK_EAGER_PROPAGATES = True
    CELERY_BROKER_URL = 'memory://'
    CELERY_RESULT_BACKEND = 'cache+memory://'
    RATELIMIT_ENABLED = False
    SECURITY_HEADERS_ENABLED = False
    METRICS_ENABLED = False
    OTEL_ENABLED = False
    LOG_FILE_ENABLED = False
    ALERT_WEBHOOK_URL = ''  # 测试不推 webhook


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
