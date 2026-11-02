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
