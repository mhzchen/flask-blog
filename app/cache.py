"""极简 Redis 缓存工具。

设计原则（也是生产要点）：
- 缓存只是"加速层"，绝不允许它拖垮业务 —— Redis 未配置或连不上时直接放行原逻辑；
- 只缓存返回 200 的 JSON 响应；
- key 由"前缀 + 请求路径 + 查询参数"组成，方便按前缀批量失效。
"""
import random
from functools import wraps

from flask import current_app, has_request_context, request
from redis import Redis
from redis.exceptions import RedisError

from app.degradation import degrade


def _client(app):
    """惰性创建 Redis 客户端，缓存在 app.extensions 里避免重复连接。"""
    if 'cache_redis' not in app.extensions:
        url = app.config.get('CACHE_REDIS_URL')
        app.extensions['cache_redis'] = Redis.from_url(url) if url else None
    return app.extensions['cache_redis']


def _bump(app, name, prefix):
    """Prometheus 缓存指标打点：metrics 未启用时零开销跳过，绝不抛错。"""
    m = app.extensions.get('metrics')
    if m is None:
        return
    bucket = m.setdefault('cache', {})
    key = (name, prefix)
    bucket[key] = bucket.get(key, 0) + 1


def cached(key_prefix, timeout=None):
    """缓存视图返回的 JSON 响应。key = key_prefix:path?query。"""
    def deco(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            app = current_app._get_current_object()
            # 任一条件不满足就直接走原逻辑，绝不让缓存变成故障点
            if not app.config.get('CACHE_ENABLED', True):
                return fn(*args, **kwargs)
            if not has_request_context():
                return fn(*args, **kwargs)
            client = _client(app)
            if client is None:
                return fn(*args, **kwargs)

            base = timeout if timeout is not None else app.config.get('CACHE_DEFAULT_TIMEOUT', 60)
            # 防雪崩：TTL 加 ±20% 随机抖动，避免大量 key 同时过期集中打穿 DB
            ttl = int(base * (0.8 + random.random() * 0.4))
            key = f"{key_prefix}:{request.path}?{request.query_string.decode('utf-8', 'ignore')}"
            try:
                hit = client.get(key)
                if hit is not None:
                    _bump(app, 'cache_hits_total', key_prefix)
                    return app.response_class(hit, status=200, mimetype='application/json')
                resp = fn(*args, **kwargs)
                if resp.status_code == 200:
                    _bump(app, 'cache_misses_total', key_prefix)
                    client.setex(key, ttl, resp.get_data())
                return resp
            except RedisError as e:
                # Redis 故障：降级为直接执行，不抛给用户
                _bump(app, 'cache_degraded_total', None)
                degrade('redis_cache', 'redis down, direct-query fallback: %s' % e, app)
                return fn(*args, **kwargs)
        return wrapper
    return deco


def invalidate(prefix):
    """删除某前缀下的所有缓存（数据变更时调用，保证读到最新）。"""
    app = current_app._get_current_object()
    client = _client(app)
    if client is None:
        return
    try:
        keys = list(client.scan_iter(match=f"{prefix}:*"))
        if keys:
            client.delete(*keys)
    except RedisError:
        pass
