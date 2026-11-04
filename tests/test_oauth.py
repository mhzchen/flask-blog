"""GitHub OAuth 登录测试（#60）。

不真正连 GitHub：monkeypatch app.api.auth.requests 的 post/get，
验证 发起(state/302) / 回调(state 校验/建用户/发 JWT/复用/冲突/网络错误)。
"""
import pytest
from app import db
from app.api import auth as auth_mod
from app.models import User

GITHUB_ID = "123456"


@pytest.fixture()
def oauth_config(app):
    app.config["GITHUB_CLIENT_ID"] = "test-client-id"
    app.config["GITHUB_CLIENT_SECRET"] = "test-client-secret"
    app.config["GITHUB_REDIRECT_URI"] = "http://localhost:5000/api/v1/auth/github/callback"
    return app


class _FakeResp:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


def _fake_token(url, **kwargs):
    return _FakeResp({"access_token": "gh-token-123"})


def _fake_user(url, headers=None, **kwargs):
    return _FakeResp({
        "id": int(GITHUB_ID), "login": "octocat", "name": "Mona Lisa",
        "email": "mona@example.com",
    })


def _begin(client):
    """走 /github/login 拿回 state（存进 client session）。"""
    r = client.get("/api/v1/auth/github/login")
    assert r.status_code == 302, r.get_json()
    return r.headers["Location"].split("state=")[1]


def test_github_login_unconfigured_503(client):
    r = client.get("/api/v1/auth/github/login")
    assert r.status_code == 503


def test_github_login_redirects_with_state(client, oauth_config):
    r = client.get("/api/v1/auth/github/login")
    assert r.status_code == 302
    loc = r.headers["Location"]
    assert "github.com/login/oauth/authorize" in loc
    assert "state=" in loc and "client_id=test-client-id" in loc


def test_github_callback_bad_state(client, oauth_config):
    r = client.get("/api/v1/auth/github/callback?code=abc&state=wrong")
    assert r.status_code == 400


def test_github_callback_missing_state(client, oauth_config):
    r = client.get("/api/v1/auth/github/callback?code=abc")
    assert r.status_code == 400


def test_github_callback_creates_user_and_jwt(client, oauth_config, monkeypatch):
    monkeypatch.setattr(auth_mod.requests, "post", _fake_token)
    monkeypatch.setattr(auth_mod.requests, "get", _fake_user)
    state = _begin(client)
    r = client.get(f"/api/v1/auth/github/callback?code=c0&state={state}")
    assert r.status_code == 302
    loc = r.headers["Location"]
    assert "oauth=github" in loc and "access_token=" in loc

    user = User.query.filter_by(github_id=GITHUB_ID).first()
    assert user is not None and user.username == "octocat"
    assert user.github_username == "Mona Lisa"
    assert user.email == "mona@example.com"
    assert user.password_hash  # GitHub 用户也必须有不可空 password_hash（随机不可登录）

    token = loc.split("access_token=")[1].split("&")[0]
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.get_json()["user"]["username"] == "octocat"
    assert me.get_json()["user"].get("github_username") == "Mona Lisa"


def test_github_callback_reuses_existing_user(client, oauth_config, monkeypatch):
    monkeypatch.setattr(auth_mod.requests, "post", _fake_token)
    monkeypatch.setattr(auth_mod.requests, "get", _fake_user)
    for _ in range(2):
        state = _begin(client)
        assert client.get(f"/api/v1/auth/github/callback?code=c0&state={state}").status_code == 302
    assert User.query.filter_by(github_id=GITHUB_ID).count() == 1


def test_github_callback_username_conflict_suffix(client, oauth_config, monkeypatch):
    u = User(username="octocat", email="octocat@example.com")
    u.set_password("secret123")
    db.session.add(u)
    db.session.commit()
    monkeypatch.setattr(auth_mod.requests, "post", _fake_token)
    monkeypatch.setattr(auth_mod.requests, "get", _fake_user)
    state = _begin(client)
    r = client.get(f"/api/v1/auth/github/callback?code=c0&state={state}")
    assert r.status_code == 302
    user = User.query.filter_by(github_id=GITHUB_ID).first()
    assert user.username == "octocat_1"


def test_github_callback_network_error_502(client, oauth_config, monkeypatch):
    import requests as real_requests

    def boom(*a, **k):
        raise real_requests.RequestException("conn refused")

    monkeypatch.setattr(auth_mod.requests, "post", boom)
    state = _begin(client)
    r = client.get(f"/api/v1/auth/github/callback?code=c0&state={state}")
    assert r.status_code == 502


def test_github_callback_no_access_token_502(client, oauth_config, monkeypatch):
    """GitHub token 端点返回错误（无 access_token）→ 502"""
    monkeypatch.setattr(auth_mod.requests, "post",
                        lambda *a, **k: _FakeResp({"error": "bad_verification_code"}))
    state = _begin(client)
    r = client.get(f"/api/v1/auth/github/callback?code=c0&state={state}")
    assert r.status_code == 502


def test_github_callback_no_user_id_502(client, oauth_config, monkeypatch):
    """GitHub user 端点返回错误（无 id）→ 502"""
    monkeypatch.setattr(auth_mod.requests, "post", _fake_token)
    monkeypatch.setattr(auth_mod.requests, "get",
                        lambda *a, **k: _FakeResp({"message": "rate limited"}))
    state = _begin(client)
    r = client.get(f"/api/v1/auth/github/callback?code=c0&state={state}")
    assert r.status_code == 502


def test_github_callback_empty_login_fallback(client, oauth_config, monkeypatch):
    """GitHub login 为空时用 gh_{id} 兜底用户名"""
    def _u(url, headers=None, **k):
        return _FakeResp({"id": int(GITHUB_ID), "login": None, "name": "N", "email": "n@e.com"})
    monkeypatch.setattr(auth_mod.requests, "post", _fake_token)
    monkeypatch.setattr(auth_mod.requests, "get", _u)
    state = _begin(client)
    r = client.get(f"/api/v1/auth/github/callback?code=c0&state={state}")
    assert r.status_code == 302
    user = User.query.filter_by(github_id=GITHUB_ID).first()
    assert user.username == f"gh_{GITHUB_ID}"
    assert user.email == "n@e.com"


def test_github_callback_no_email_noreply(client, oauth_config, monkeypatch):
    """GitHub 不返回 email（默认隐藏）时用 noreply 兜底邮箱"""
    def _u(url, headers=None, **k):
        return _FakeResp({"id": int(GITHUB_ID), "login": "noemail", "name": "NE", "email": None})
    monkeypatch.setattr(auth_mod.requests, "post", _fake_token)
    monkeypatch.setattr(auth_mod.requests, "get", _u)
    state = _begin(client)
    r = client.get(f"/api/v1/auth/github/callback?code=c0&state={state}")
    assert r.status_code == 302
    user = User.query.filter_by(github_id=GITHUB_ID).first()
    assert user.username == "noemail"
    assert user.email == "noemail@users.noreply.github.com"
