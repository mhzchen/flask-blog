"""Redis 缓存装饰器与失效逻辑测试（用内存 FakeRedis，不依赖真实 Redis）。"""
import pytest
from redis.exceptions import RedisError

from app.cache import cached, invalidate


class FakeRedis:
    def __init__(self):
        self.store = {}

    def get(self, key):
        return self.store.get(key)

    def setex(self, key, ttl, value):
        self.store[key] = value

    def scan_iter(self, match=None):
        prefix = match[:-1] if match and match.endswith('*') else match or ''
        return [k for k in self.store if k.startswith(prefix)]

    def delete(self, *keys):
        for k in keys:
            self.store.pop(k, None)


def _register(app, path, name, view):
    app.add_url_rule(path, name, view)
    return app.test_client()


def _cached_view(app, calls, prefix, timeout=None):
    """返回一个套了 cached 装饰器的视图函数。"""
    def fn():
        calls['n'] += 1
        return app.response_class('{"ok":1}', status=200, mimetype='application/json')
    return cached(prefix, timeout=timeout)(fn)


def test_cache_miss_then_hit(app):
    app.config['CACHE_ENABLED'] = True
    app.extensions['cache_redis'] = FakeRedis()
    calls = {'n': 0}
    c = _register(app, '/cache/x', 'cx', _cached_view(app, calls, 'posts'))
    assert c.get('/cache/x').status_code == 200
    assert c.get('/cache/x').status_code == 200
    assert calls['n'] == 1  # 第二次命中缓存，未再执行原函数


def test_cache_disabled_passthrough(app):
    app.config['CACHE_ENABLED'] = False
    app.extensions['cache_redis'] = FakeRedis()
    calls = {'n': 0}
    c = _register(app, '/cache/y', 'cy', _cached_view(app, calls, 'posts'))
    c.get('/cache/y')
    c.get('/cache/y')
    assert calls['n'] == 2  # 禁用缓存时每次都走原逻辑


def test_cache_no_client_passthrough(app):
    app.config['CACHE_ENABLED'] = True
    app.config['CACHE_REDIS_URL'] = None
    app.extensions.pop('cache_redis', None)  # 强制 _client 返回 None
    calls = {'n': 0}
    c = _register(app, '/cache/w', 'cw', _cached_view(app, calls, 'posts'))
    c.get('/cache/w')
    assert calls['n'] == 1


def test_cache_redis_error_degrades(app):
    app.config['CACHE_ENABLED'] = True
    class Boom(FakeRedis):
        def get(self, key):
            raise RedisError('redis down')
    app.extensions['cache_redis'] = Boom()
    calls = {'n': 0}
    c = _register(app, '/cache/z', 'cz', _cached_view(app, calls, 'posts'))
    resp = c.get('/cache/z')
    assert resp.status_code == 200
    assert calls['n'] == 1  # Redis 故障时降级执行原函数，不抛错


def test_invalidate_clears_prefix(app):
    client = FakeRedis()
    client.store['posts:1'] = b'1'
    client.store['posts:2'] = b'2'
    client.store['categories:1'] = b'3'
    app.extensions['cache_redis'] = client
    invalidate('posts')
    assert 'posts:1' not in client.store
    assert 'posts:2' not in client.store
    assert 'categories:1' in client.store  # 其它前缀不受影响