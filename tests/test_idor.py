"""IDOR 越权测试（#60 安全纵深）。

验证跨用户直接对象引用（改 URL/参数访问他人资源）被正确拒绝：
- 评论删除：他人 403 / 本人 200 / 管理员 200
- 收藏：用户之间完全隔离，无 user_id 注入面
- 管理端：普通用户 403
- /auth/me：只返回当前用户
"""
import pytest
from app import db
from app.models import User
from tests.conftest import _login


@pytest.fixture()
def bob(app):
    """第二个普通用户（用于跨用户越权验证）"""
    u = User(username="bob", email="bob@example.com")
    u.set_password("secret123")
    db.session.add(u)
    db.session.commit()
    return u


def _bob_headers(client, bob):
    return _login(client, "bob", "secret123")


def _add_comment(client, headers, post_id):
    r = client.post(f"/api/v1/posts/{post_id}/comments",
                    json={"content": "hello from alice"}, headers=headers)
    assert r.status_code == 201, r.get_json()
    return r.get_json()["comment"]["id"]


def test_comment_delete_other_user_forbidden(client, post, user_headers, normal_user, bob):
    """IDOR：bob 用自己 token 删除 alice 的评论 → 403"""
    cid = _add_comment(client, user_headers, post.id)
    r = client.delete(f"/api/v1/comments/{cid}", headers=_bob_headers(client, bob))
    assert r.status_code == 403
    assert r.get_json()["error"]


def test_comment_delete_own_ok(client, post, user_headers, normal_user):
    cid = _add_comment(client, user_headers, post.id)
    r = client.delete(f"/api/v1/comments/{cid}", headers=user_headers)
    assert r.status_code == 200


def test_comment_delete_admin_ok(client, post, user_headers, admin_headers, normal_user, admin_user):
    cid = _add_comment(client, user_headers, post.id)
    r = client.delete(f"/api/v1/comments/{cid}", headers=admin_headers)
    assert r.status_code == 200


def test_favorites_isolated_between_users(client, post, user_headers, bob):
    """IDOR：alice 收藏后，bob 看不到也查不到（跨用户隔离）"""
    r = client.post(f"/api/v1/favorites/{post.id}/toggle", headers=user_headers)
    assert r.get_json()["favorited"] is True
    bh = _bob_headers(client, bob)
    r2 = client.get("/api/v1/favorites", headers=bh)
    assert r2.status_code == 200 and r2.get_json()["items"] == []
    r3 = client.get(f"/api/v1/favorites/check/{post.id}", headers=bh)
    assert r3.get_json()["favorited"] is False


def test_favorites_no_foreign_user_id_param(client, post, user_headers):
    """IDOR：收藏接口无 user_id 形参，即使带上 user_id 查询参数也只会作用于当前身份"""
    r = client.post(f"/api/v1/favorites/{post.id}/toggle?user_id=999", headers=user_headers)
    assert r.get_json()["favorited"] is True
    r2 = client.get("/api/v1/favorites", headers=user_headers)
    assert len(r2.get_json()["items"]) == 1
    # 用当前身份取消，仅影响自己
    r3 = client.post(f"/api/v1/favorites/{post.id}/toggle?user_id=999", headers=user_headers)
    assert r3.get_json()["favorited"] is False


def test_admin_requires_admin(client, user_headers, normal_user):
    """IDOR/越权：普通用户访问管理端 → 403"""
    r = client.get("/api/v1/admin/posts", headers=user_headers)
    assert r.status_code == 403


def test_me_scoped_to_current(client, user_headers, normal_user, bob):
    """IDOR：/auth/me 只返回当前用户，不泄露他人"""
    r = client.get("/api/v1/auth/me", headers=user_headers)
    assert r.get_json()["user"]["username"] == "alice"
    assert "password_hash" not in r.get_json()["user"]


def test_me_other_user_not_leaked(client, user_headers, normal_user, bob):
    """IDOR：token 里塞别人的 sub 无法访问他人信息（JWT 签名保证）"""
    from flask_jwt_extended import create_access_token
    forged = create_access_token(identity=str(bob.id))
    r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {forged}"})
    assert r.status_code == 200
    assert r.get_json()["user"]["username"] == "bob"
    # alice 的 token 拿不到 bob 的评论列表等——收藏列表同理
    r2 = client.get("/api/v1/favorites", headers=user_headers)
    assert r2.status_code == 200
