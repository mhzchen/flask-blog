"""服务层（Service）单元测试：直接测业务规则，不走 HTTP。

与 test_*.py 的 HTTP 集成测试互补：这里直测 service 方法，
重点覆盖 HTTP 集成测试不易触达的异常分支（唯一性冲突、权限、空值校验）。
"""
import pytest
from app.services import (
    ServiceError,
    admin_post_service,
    auth_service,
    category_service,
    comment_service,
    favorite_service,
    post_service,
)

# ---------------- AuthService ----------------

def test_register_duplicate_username(app, normal_user):
    with pytest.raises(ServiceError) as e:
        auth_service.register('alice', 'x@y.com', 'secret123')
    assert e.value.status_code == 409


def test_register_duplicate_email(app, normal_user):
    with pytest.raises(ServiceError) as e:
        auth_service.register('bob2', 'alice@example.com', 'secret123')
    assert e.value.status_code == 409


def test_register_ok(app):
    u = auth_service.register('carol', 'carol@example.com', 'secret123')
    assert u.id is not None
    assert u.check_password('secret123')


def test_login_wrong_password(app, normal_user):
    assert auth_service.login('alice', 'wrongpass') is None


def test_login_ok(app, normal_user):
    u = auth_service.login('alice', 'secret123')
    assert u is not None and u.username == 'alice'


def test_get_or_404_missing(app):
    with pytest.raises(ServiceError) as e:
        auth_service.get_or_404(99999)
    assert e.value.status_code == 404


# ---------------- CommentService ----------------

def test_comment_create_empty_content(app, post, normal_user):
    with pytest.raises(ServiceError) as e:
        comment_service.create(post.id, normal_user.id, '   ')
    assert e.value.status_code == 422


def test_comment_delete_forbidden(app, post, normal_user, admin_user):
    c = comment_service.create(post.id, normal_user.id, '你好')
    other = auth_service.register('other', 'other@x.com', 'secret123')
    with pytest.raises(ServiceError) as e:
        comment_service.delete(c.id, other)
    assert e.value.status_code == 403


def test_comment_delete_admin_ok(app, post, normal_user, admin_user):
    c = comment_service.create(post.id, normal_user.id, '你好')
    comment_service.delete(c.id, admin_user)
    assert c.id  # 已删除，无异常


def test_comment_delete_missing(app, normal_user):
    with pytest.raises(ServiceError) as e:
        comment_service.delete(99999, normal_user)
    assert e.value.status_code == 404


# ---------------- FavoriteService ----------------

def test_favorite_toggle_flow(app, post, normal_user):
    assert favorite_service.check(normal_user.id, post.id) is False
    assert favorite_service.toggle(normal_user.id, post.id) is True
    assert favorite_service.check(normal_user.id, post.id) is True
    assert favorite_service.toggle(normal_user.id, post.id) is False
    assert favorite_service.check(normal_user.id, post.id) is False


# ---------------- CategoryService ----------------

def test_category_create_duplicate_slug(app, category):
    with pytest.raises(ServiceError) as e:
        category_service.create('重名', 'python')
    assert e.value.status_code == 409


def test_category_get_or_404(app):
    with pytest.raises(ServiceError) as e:
        category_service.get_or_404(99999)
    assert e.value.status_code == 404


# ---------------- AdminPostService ----------------

def test_require_admin_denied(app, normal_user):
    with pytest.raises(ServiceError) as e:
        admin_post_service.require_admin(normal_user.id)
    assert e.value.status_code == 403


def test_require_admin_ok(app, admin_user):
    admin_post_service.require_admin(admin_user.id)  # 无异常即通过


def test_admin_create_post_missing_category(app):
    with pytest.raises(ServiceError) as e:
        admin_post_service.create('标题', '摘要', '<p>x</p>', 99999, [])
    assert e.value.status_code == 400


# ---------------- PostService ----------------

def test_post_get_detail_missing(app):
    # 文章不存在由 repository 的 abort() 抛 HTTPException(404)
    from werkzeug.exceptions import HTTPException
    with pytest.raises(HTTPException) as e:
        post_service.get_detail(99999)
    assert e.value.code == 404
