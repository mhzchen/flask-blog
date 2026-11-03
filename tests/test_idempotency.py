# -*- coding: utf-8 -*-
"""#55 接口幂等性测试：带 Idempotency-Key 的重复写请求只执行一次业务。"""
import pytest


class FakeRedis:
    """内存版 Redis 桩：仅实现幂等用到的 get/setex。"""
    def __init__(self):
        self.store = {}

    def get(self, key):
        return self.store.get(key)

    def setex(self, key, ttl, value):
        self.store[key] = value


@pytest.fixture()
def fake_redis(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr('app.idempotency._client', lambda app: fake)
    return fake


def test_idempotent_replay_returns_first_response(client, fake_redis, post, user_headers):
    """同 Idempotency-Key 两次提交：返回首次结果，评论只创建一条。"""
    headers = {**user_headers, 'Idempotency-Key': 'key-comment-001'}
    r1 = client.post(f'/api/v1/posts/{post.id}/comments', json={'content': '幂等评论'}, headers=headers)
    assert r1.status_code == 201
    first_id = r1.get_json()['comment']['id']

    r2 = client.post(f'/api/v1/posts/{post.id}/comments', json={'content': '幂等评论'}, headers=headers)
    assert r2.status_code == 201
    assert r2.get_json()['comment']['id'] == first_id

    items = client.get(f'/api/v1/posts/{post.id}/comments').get_json()['items']
    assert len(items) == 1


def test_no_key_creates_twice(client, post, user_headers):
    """不带 Idempotency-Key：正常创建两条（幂等只对带 key 的请求生效）。"""
    client.post(f'/api/v1/posts/{post.id}/comments', json={'content': 'a'}, headers=user_headers)
    client.post(f'/api/v1/posts/{post.id}/comments', json={'content': 'b'}, headers=user_headers)
    items = client.get(f'/api/v1/posts/{post.id}/comments').get_json()['items']
    assert len(items) == 2


def test_idempotent_degrades_without_redis(client, post, user_headers):
    """Redis 不可用（无 CACHE_REDIS_URL → _client 返回 None）：降级直接执行。"""
    headers = {**user_headers, 'Idempotency-Key': 'key-degrade'}
    r = client.post(f'/api/v1/posts/{post.id}/comments', json={'content': '降级'}, headers=headers)
    assert r.status_code == 201


def test_idempotent_redis_error_degrades(client, post, user_headers, monkeypatch):
    """Redis 调用抛 RedisError：幂等降级直接执行（不抛给用户）。"""
    from redis.exceptions import RedisError

    class Boom:
        def get(self, k):
            raise RedisError('redis down')

        def setex(self, k, t, v):
            raise RedisError('redis down')

    monkeypatch.setattr('app.idempotency._client', lambda app: Boom())
    headers = {**user_headers, 'Idempotency-Key': 'key-boom'}
    r = client.post(f'/api/v1/posts/{post.id}/comments', json={'content': 'x'}, headers=headers)
    assert r.status_code == 201
