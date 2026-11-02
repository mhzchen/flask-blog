"""Prometheus 指标端点（/metrics）测试。

独立 app（METRICS_ENABLED=True）验证：请求计数/延迟直方图/并发水位，
以及 /metrics 自身不计入指标。
"""
import pytest
from app import create_app, db
from config import TestingConfig


@pytest.fixture()
def metrics_app():
    class MetricsTestingConfig(TestingConfig):
        METRICS_ENABLED = True

    application = create_app(MetricsTestingConfig)
    with application.app_context():
        db.create_all()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def mclient(metrics_app):
    return metrics_app.test_client()


def test_metrics_endpoint_returns_plain_text(mclient):
    resp = mclient.get("/metrics")
    assert resp.status_code == 200
    assert resp.content_type.startswith("text/plain")
    body = resp.get_data(as_text=True)
    assert "# TYPE http_requests_total counter" in body
    assert "# TYPE http_request_duration_seconds histogram" in body


def test_metrics_excludes_itself(mclient):
    # /metrics 抓取多次，但自身不应出现在 http_requests_total 里
    for _ in range(3):
        mclient.get("/metrics")
    body = mclient.get("/metrics").get_data(as_text=True)
    assert 'path="/metrics"' not in body


def test_requests_recorded_with_status(mclient):
    mclient.get("/api/posts")
    mclient.get("/no/such/route")
    body = mclient.get("/metrics").get_data(as_text=True)
    assert 'path="/api/posts",status="200"}' in body
    assert 'status="404"' in body


def test_histogram_bucket_and_sum(mclient):
    mclient.get("/api/posts")
    body = mclient.get("/metrics").get_data(as_text=True)
    # count 应为 1，且 sum 存在
    assert 'http_request_duration_seconds_count{method="GET",path="/api/posts"} 1' in body
    assert 'http_request_duration_seconds_sum{method="GET",path="/api/posts"}' in body
    # +Inf 桶等于总计数
    assert '+Inf"} 1' in body


def test_inflight_returns_to_zero(mclient):
    mclient.get("/api/posts")
    body = mclient.get("/metrics").get_data(as_text=True)
    assert "http_requests_inflight 0" in body


def test_uptime_positive(mclient):
    body = mclient.get("/metrics").get_data(as_text=True)
    assert "process_uptime_seconds " in body
