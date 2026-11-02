"""Prometheus 指标端点（/metrics）。

可观测性纵深：日志（结构化 JSON）+ 健康检查（/health、/healthz）+ 慢查询日志，
再加上这一环——指标。暴露 Prometheus 文本格式（text/plain; version=0.0.4），
可直接被 Prometheus 抓取 / 接入 Grafana 做面板与告警。

指标：
- http_requests_total{method,path,status}  请求量计数（按状态码分类）
- http_request_duration_seconds{method,path}  请求延迟直方图（累计桶 + sum + count）
- http_requests_inflight  当前正在处理的请求数（并发水位）
- process_uptime_seconds  进程存活时间

设计：
- 状态存在 app.extensions["metrics"]，每个 app 实例独立，多进程/多测试互不干扰；
- METRICS_ENABLED 控制开关（生产/开发默认开，测试关）；
- /metrics 自身不计入指标，避免"抓取产生指标"的自增噪声。
"""
import time

from flask import g, request

# 直方图桶（秒）：覆盖 10ms~10s，够看压测与慢接口的延迟分布
_BUCKETS = (0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)


def _new_state():
    return {
        "counters": {},        # (method, path, status) -> int
        "hist_sum": {},        # (method, path) -> float 秒
        "hist_count": {},      # (method, path) -> int
        "hist_buckets": {},    # (method, path, le) -> int
        "inflight": 0,
        "start": time.time(),
    }


def _record(state, method, path, status, dur_s):
    key = (method, path, status)
    state["counters"][key] = state["counters"].get(key, 0) + 1
    hk = (method, path)
    state["hist_sum"][hk] = state["hist_sum"].get(hk, 0.0) + dur_s
    state["hist_count"][hk] = state["hist_count"].get(hk, 0) + 1
    for le in _BUCKETS:
        bk = (method, path, le)
        if dur_s <= le:
            state["hist_buckets"][bk] = state["hist_buckets"].get(bk, 0) + 1


def register_metrics(app):
    """注册 /metrics 路由与请求打点钩子。"""
    if not app.config.get("METRICS_ENABLED", True):
        return
    state = _new_state()
    app.extensions["metrics"] = state

    @app.before_request
    def _start():
        if request.path == "/metrics":
            return
        g._metrics_start = time.perf_counter()
        state["inflight"] += 1

    @app.after_request
    def _finish(resp):
        start = getattr(g, "_metrics_start", None)
        if start is None:
            return resp
        dur = time.perf_counter() - start
        state["inflight"] -= 1
        _record(state, request.method, request.path, resp.status_code, dur)
        return resp

    @app.get("/metrics")
    def metrics():
        body = render_metrics(state)
        return body, 200, {"Content-Type": "text/plain; version=0.0.4; charset=utf-8"}


def _db_pool():
    """Read SQLAlchemy connection pool counters as dict.

    Pool.status() returns a human string (not a dict), so read counters
    individually; both QueuePool methods (checkedout()/checkedin()/size()/
    overflow()) and StaticPool attributes (size) are supported.
    """
    try:
        from app import db
        p = db.engine.pool
    except Exception:
        return {}
    info = {}
    for name in ("checkedout", "checkedin", "size", "overflow"):
        attr = getattr(p, name, None)
        if attr is None:
            info[name] = 0
            continue
        try:
            val = attr() if callable(attr) else attr
        except Exception:
            val = 0
        info[name] = val if isinstance(val, int) else 0
    return info


def render_metrics(state):
    """把状态渲染为 Prometheus 文本格式。"""
    lines = [
        "# HELP http_requests_total Total requests by method, path and status code",
        "# TYPE http_requests_total counter",
    ]
    for (method, path, status), n in sorted(state["counters"].items()):
        lines.append(
            'http_requests_total{method="%s",path="%s",status="%s"} %d' % (method, path, status, n)
        )

    lines.append("# HELP http_request_duration_seconds HTTP request duration in seconds")
    lines.append("# TYPE http_request_duration_seconds histogram")
    for hk in sorted(state["hist_count"].keys()):
        method, path = hk
        label = 'method="%s",path="%s"' % (method, path)
        running = 0
        for le in _BUCKETS:
            running += state["hist_buckets"].get((method, path, le), 0)
            lines.append(
                'http_request_duration_seconds_bucket{%s,le="%s"} %d' % (label, le, running)
            )
        cnt = state["hist_count"][hk]
        sm = state["hist_sum"][hk]
        lines.append(
            'http_request_duration_seconds_bucket{%s,le="+Inf"} %d' % (label, cnt)
        )
        lines.append("http_request_duration_seconds_sum{%s} %.6f" % (label, sm))
        lines.append("http_request_duration_seconds_count{%s} %d" % (label, cnt))

    lines.append("# HELP http_requests_inflight Number of requests currently in flight")
    lines.append("# TYPE http_requests_inflight gauge")
    lines.append("http_requests_inflight %d" % state["inflight"])

    lines.append("# HELP cache_hits_total Redis cache hits by prefix")
    lines.append("# TYPE cache_hits_total counter")
    for (name, prefix), n in sorted(state.get("cache", {}).items()):
        if name == "cache_hits_total" and prefix:
            lines.append('cache_hits_total{prefix="%s"} %d' % (prefix, n))

    lines.append("# HELP cache_misses_total Redis cache misses (re-fetch) by prefix")
    lines.append("# TYPE cache_misses_total counter")
    for (name, prefix), n in sorted(state.get("cache", {}).items()):
        if name == "cache_misses_total":
            lines.append('cache_misses_total{prefix="%s"} %d' % (prefix, n))

    lines.append("# HELP cache_degraded_total Redis down, degraded to direct query")
    lines.append("# TYPE cache_degraded_total counter")
    for (name, _prefix), n in sorted(state.get("cache", {}).items()):
        if name == "cache_degraded_total":
            lines.append("cache_degraded_total %d" % n)

    lines.append("# HELP db_pool_checkedout SQLAlchemy pool connections checked out")
    lines.append("# TYPE db_pool_checkedout gauge")
    lines.append("db_pool_checkedout %d" % _db_pool().get("checkedout", 0))

    lines.append("# HELP db_pool_checkedin SQLAlchemy pool idle connections")
    lines.append("# TYPE db_pool_checkedin gauge")
    lines.append("db_pool_checkedin %d" % _db_pool().get("checkedin", 0))

    lines.append("# HELP db_pool_size SQLAlchemy pool current size")
    lines.append("# TYPE db_pool_size gauge")
    lines.append("db_pool_size %d" % _db_pool().get("size", 0))

    lines.append("# HELP process_uptime_seconds Uptime of the process in seconds")
    lines.append("# TYPE process_uptime_seconds gauge")
    lines.append("process_uptime_seconds %.1f" % (time.time() - state["start"]))

    return "\n".join(lines) + "\n"
