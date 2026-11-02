"""安全纵深测试：安全响应头 / 登录锁定 / 密码强度。"""

import pytest
from app import create_app, db
from app.models import User
from app.services import ServiceError, auth_service
from sqlalchemy.pool import StaticPool


def _make_app():
    class SecConfig:
        TESTING = True
        SQLALCHEMY_DATABASE_URI = "sqlite://"
        SQLALCHEMY_TRACK_MODIFICATIONS = False
        SQLALCHEMY_ENGINE_OPTIONS = {
            "poolclass": StaticPool, "connect_args": {"check_same_thread": False}}
        SECRET_KEY = "sec-test-secret"
        JWT_SECRET_KEY = "sec-test-jwt"
        CACHE_ENABLED = False
        CELERY_TASK_ALWAYS_EAGER = True
        RATELIMIT_ENABLED = False
        SECURITY_HEADERS_ENABLED = True
        LOGIN_MAX_FAILURES = 3
        LOGIN_LOCKOUT_SECONDS = 300
    return create_app(SecConfig)


def _seed_user(app, username="alice", password="secret123", admin=False):
    with app.app_context():
        u = User(username=username, email=f"{username}@e.com", is_admin=admin)
        u.set_password(password)
        db.session.add(u)
        db.session.commit()


# ---------------- 安全响应头 ----------------

def test_security_headers_present():
    app = _make_app()
    client = app.test_client()
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.headers.get("X-Frame-Options") == "DENY"
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("Content-Security-Policy", "").startswith("default-src 'self'")
    assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"


def test_security_headers_disabled_in_testing(app):
    # 默认 TestingConfig 关闭安全头，避免其它测试断言被头干扰
    resp = app.test_client().get("/health")
    assert resp.headers.get("X-Frame-Options") is None


# ---------------- 登录锁定 ----------------

def test_login_lockout_after_failures(app):
    from app.services import _LOGIN_FAILURES
    with app.app_context():
        _LOGIN_FAILURES.clear()
        app.config["LOGIN_MAX_FAILURES"] = 3
    _seed_user(app)
    client = app.test_client()
    codes = []
    for _ in range(4):
        r = client.post("/api/auth/login",
                        json={"username": "alice", "password": "wrongpass"})
        codes.append(r.status_code)
    # 前 3 次 401，第 4 次（已达阈值）应锁定返回 429
    assert codes[:3] == [401, 401, 401]
    assert codes[3] == 429


def test_login_lockout_cleared_on_success(app):
    from app.services import _LOGIN_FAILURES
    with app.app_context():
        _LOGIN_FAILURES.clear()
    _seed_user(app)
    client = app.test_client()
    # 一次失败后正确登录应成功（失败计数只影响锁定，正确密码可登录）
    client.post("/api/auth/login", json={"username": "alice", "password": "wrongpass"})
    r = client.post("/api/auth/login", json={"username": "alice", "password": "secret123"})
    assert r.status_code == 200


# ---------------- 密码强度 ----------------

def test_register_weak_password_rejected(app):
    with app.app_context():
        with pytest.raises(ServiceError) as e:
            auth_service.register("w1", "w1@e.com", "123456")
        assert e.value.status_code == 422


def test_register_digits_only_rejected(app):
    with app.app_context():
        with pytest.raises(ServiceError) as e:
            auth_service.register("w2", "w2@e.com", "12345678")
        assert e.value.status_code == 422


def test_register_strong_password_ok(app):
    with app.app_context():
        u = auth_service.register("w3", "w3@e.com", "strong123")
        assert u is not None



# ---------------- 登录锁定：Redis 共享（多 worker/多实例） ----------------

class FakeRedis:
    """内存 Redis 替身：支持登录锁定需要的 incr/expire/get/delete。"""
    def __init__(self):
        self.store = {}
        self.ttls = {}

    def incr(self, key):
        self.store[key] = self.store.get(key, 0) + 1
        return self.store[key]

    def expire(self, key, ttl):
        self.ttls[key] = ttl

    def get(self, key):
        return self.store.get(key)

    def delete(self, *keys):
        for k in keys:
            self.store.pop(k, None)
            self.ttls.pop(k, None)


def test_login_lockout_shared_redis(app):
    """计数落在 Redis：即使本进程 dict 无记录，也能判定锁定（多实例共享生效）。"""
    from app.services import _record_failure, _is_locked, _clear_failures, _LOGIN_FAILURES
    r = FakeRedis()
    with app.app_context():
        _LOGIN_FAILURES.clear()
        app.extensions['cache_redis'] = r
        app.config['LOGIN_MAX_FAILURES'] = 3
        for _ in range(3):
            _record_failure('bob')
        # 达到阈值锁定
        assert _is_locked('bob') is True
        # 计数在 Redis，而非进程内 dict（模拟另一 worker 无本地计数也能锁定）
        assert r.store.get('login_fail:bob') == 3
        assert _LOGIN_FAILURES.get('bob') is None
        # 锁定窗口 TTL 已设置（Redis EXPIRE 生效）
        assert r.ttls.get('login_fail:bob') == app.config['LOGIN_LOCKOUT_SECONDS']
        # 成功登录解锁：Redis key 清除，不再锁定
        _clear_failures('bob')
        assert _is_locked('bob') is False
        assert r.store.get('login_fail:bob') is None


def test_login_lockout_redis_disabled_fallback_dict(app):
    """关闭 Redis 共享（或 Redis 不可用）时降级为进程内 dict，单机仍能锁定。"""
    from app.services import _record_failure, _is_locked, _LOGIN_FAILURES
    with app.app_context():
        _LOGIN_FAILURES.clear()
        app.config['LOGIN_REDIS_ENABLED'] = False
        app.config['LOGIN_MAX_FAILURES'] = 3
        for _ in range(3):
            _record_failure('carol')
        assert _is_locked('carol') is True
        # 计数落在进程内 dict
        assert _LOGIN_FAILURES.get('carol') is not None
