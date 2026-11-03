"""OpenTelemetry 全链路追踪 配置与幂等性测试（不启动真实 OTel，避免污染测试环境）。"""
from app.telemetry import _current_trace_id, init_telemetry


def test_current_trace_id_none_without_span():
    """无活动 span 时 _current_trace_id 返回 None（日志不注入 trace_id 字段）。"""
    assert _current_trace_id() is None


def test_testing_config_disables_otel(app):
    """TestingConfig 显式关闭 OTel，避免 instrumentation 污染 pytest。"""
    assert app.config['OTEL_ENABLED'] is False


def test_init_telemetry_noop_when_disabled(app):
    """OTEL_ENABLED=False 时 init_telemetry 为 no-op 且幂等可重复调用。"""
    init_telemetry(app)
    init_telemetry(app)  # 重复调用不抛错
