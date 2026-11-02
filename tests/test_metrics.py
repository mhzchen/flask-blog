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



# ---------------- 缓存指标打点 ----------------

def test_cache_hit_miss_metrics(mclient, metrics_app):
    # 用一个走 cached 装饰器的视图验证命中/未命中计数
    # 注入一个内存版 Redis 客户端（test_cache.py 同款），验证命中/未命中计数
    from app.cache import cached

    class FakeRedis:
        def __init__(self):
            self.store = {}
        def get(self, key):
            return self.store.get(key)
        def setex(self, key, ttl, value):
            self.store[key] = value
        def scan_iter(self, match=None):
            prefix = match[:-1] if match and match.endswith("*") else (match or "")
            return [k for k in self.store if k.startswith(prefix)]
        def delete(self, *keys):
            for k in keys:
                self.store.pop(k, None)

    metrics_app.config["CACHE_ENABLED"] = True
    metrics_app.extensions["cache_redis"] = FakeRedis()

    from app.cache import cached
    from flask import jsonify
    calls = {"n": 0}

    @metrics_app.get("/cache/cat")
    @cached("cats")
    def cats():
        calls["n"] += 1
        return jsonify({"ok": 1})

    c = metrics_app.test_client()
    c.get("/cache/cat")   # miss -> 建缓存
    c.get("/cache/cat")   # hit
    body = c.get("/metrics").get_data(as_text=True)
    assert 'cache_misses_total{prefix="cats"} 1' in body
    assert 'cache_hits_total{prefix="cats"} 1' in body


def test_db_pool_metrics_present(mclient):
    body = mclient.get("/metrics").get_data(as_text=True)
    assert "db_pool_checkedout " in body
    assert "db_pool_checkedin " in body
    assert "db_pool_size " in body
