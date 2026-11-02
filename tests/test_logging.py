"""日志可观测性测试：慢请求采样 + 慢 SQL 日志携带 request_id（可与请求串联排查）。"""
import logging


def _collect(app, fn):
    """在 app.logger 上挂临时 handler，收集请求期间产生的日志 record。"""
    collected = []

    class _H(logging.Handler):
        def emit(self, record):
            collected.append(record)

    h = _H()
    h.setLevel(logging.DEBUG)
    app.logger.addHandler(h)
    try:
        fn()
    finally:
        app.logger.removeHandler(h)
    return collected


def test_slow_request_logs_warning_with_rid(app):
    """整请求耗时超阈值时应额外记录 slow_request WARNING，且带上与响应一致的 request_id。"""
    app.config["SLOW_REQUEST_MS"] = 0
    app.config["SLOW_REQUEST_SAMPLE_RATE"] = 1.0
    resp = {}

    def do():
        resp["r"] = app.test_client().get("/health")

    records = _collect(app, do)
    rid = resp["r"].headers.get("X-Request-Id")
    slow = [r for r in records if r.getMessage() == "slow_request"]
    assert slow, "慢请求应记录 WARNING"
    assert slow[0].__dict__.get("rid") == rid, "慢请求日志应带与响应一致的 request_id"
    assert slow[0].__dict__.get("dur_ms") is not None


def test_slow_query_log_includes_rid(app):
    """慢 SQL 日志应携带当前请求的 request_id，便于把慢查询串联到具体请求。"""
    app.config["SLOW_QUERY_MS"] = 0
    resp = {}

    def do():
        resp["r"] = app.test_client().get("/healthz")  # 触发 SELECT 1

    records = _collect(app, do)
    rid = resp["r"].headers.get("X-Request-Id")
    sq = [r for r in records if r.getMessage() == "slow_query"]
    assert sq, "应记录 slow_query 警告"
    assert any(r.__dict__.get("rid") == rid for r in sq), "slow_query 应带与响应一致的 request_id"


def test_slow_request_sampling_rate_zero_disables(app):
    """采样率为 0 时慢请求不额外记录（用于高流量环境关闭洪峰）。"""
    app.config["SLOW_REQUEST_MS"] = 0
    app.config["SLOW_REQUEST_SAMPLE_RATE"] = 0.0

    def do():
        app.test_client().get("/health")

    records = _collect(app, do)
    slow = [r for r in records if r.getMessage() == "slow_request"]
    assert not slow, "采样率为 0 时不应记录 slow_request"
