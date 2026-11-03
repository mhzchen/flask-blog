"""OpenTelemetry 全链路追踪：HTTP -> DB -> Redis -> Celery 一条 trace。

启动方式（app/__init__.py 的 create_app 内调用 init_telemetry）：
  - OTEL_ENABLED 为真时初始化 TracerProvider，并给 Flask / SQLAlchemy / Redis / Celery 装上
    官方 instrumentation，自动在每个请求产生一条跨 HTTP/DB/Redis/异步任务的分布式 trace。
  - 导出：配了 OTEL_EXPORTER_OTLP_ENDPOINT 走 OTLP（接 Jaeger/Tempo/OTel Collector）；
    未配置则用 ConsoleSpanExporter 直接输出到 stdout（开发/无 collector 时直观观察）。
  - 每个 span 携带 trace_id，结构化日志经 _current_trace_id() 写入同名字段，可与 trace 串联。
"""
import logging

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

_initialized = False
_logger = logging.getLogger('app.telemetry')


def _current_trace_id():
    """取当前 span 的 trace_id（32 位十六进制）；无活动 span 返回 None。"""
    try:
        span = trace.get_current_span()
        ctx = span.get_span_context()
        if ctx and ctx.trace_id and ctx.trace_id != 0:
            return format(ctx.trace_id, '032x')
    except Exception:
        pass
    return None


def _setup_provider(app):
    """按配置创建并安装全局 TracerProvider（仅一次）。"""
    resource = Resource.create({
        'service.name': app.config.get('OTEL_SERVICE_NAME', 'flask-blog'),
        'service.version': app.config.get('OTEL_SERVICE_VERSION', '1.0.0'),
    })
    provider = TracerProvider(resource=resource)
    endpoint = app.config.get('OTEL_EXPORTER_OTLP_ENDPOINT', '')
    if endpoint:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
        _logger.info('OpenTelemetry exporter -> OTLP %s', endpoint)
    else:
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
        _logger.info('OpenTelemetry exporter -> console')
    trace.set_tracer_provider(provider)


def init_telemetry(app):
    """初始化全链路追踪。OTEL_ENABLED 为假或已初始化则跳过（幂等，多 app 安全）。"""
    global _initialized
    if not app.config.get('OTEL_ENABLED', False) or _initialized:
        return
    _initialized = True
    _setup_provider(app)

    from opentelemetry.instrumentation.celery import CeleryInstrumentor
    from opentelemetry.instrumentation.flask import FlaskInstrumentor
    from opentelemetry.instrumentation.redis import RedisInstrumentor
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

    FlaskInstrumentor().instrument_app(app)
    # 每个 SQLAlchemy engine（读写分离后含 default 主库与 slave 从库）都埋点。
    # engines 属性基于 current_app，需在应用上下文中访问（create_app 期间未 push）
    with app.app_context():
        for engine in app.extensions['sqlalchemy'].engines.values():
            SQLAlchemyInstrumentor().instrument(engine=engine)
    RedisInstrumentor().instrument()
    CeleryInstrumentor().instrument()
    _logger.info('OpenTelemetry 全链路追踪已启用（Flask/SQLAlchemy/Redis/Celery）')
