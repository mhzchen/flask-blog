"""文章评论接口测试：列表、发表、删除与权限控制"""
from app.models import Comment, User, db


def _make_user(username, email=None):
    u = User(username=username, email=email or f'{username}@example.com')
    u.set_password('secret123')
    db.session.add(u)
    db.session.commit()
    return u


def _login_user(client, username, password):
    r = client.post('/api/auth/login', json={'username': username, 'password': password})
    assert r.status_code == 200
    return {'Authorization': f"Bearer {r.get_json()['access_token']}"}


def _add_comment(post, user, content):
    c = Comment(content=content, post_id=post.id, user_id=user.id)
    db.session.add(c)
    db.session.commit()
    return c


# ---------- 发表评论 ----------

def test_create_comment_requires_auth(client, post):
    resp = client.post(f'/api/posts/{post.id}/comments', json={'content': 'hi'})
    assert resp.status_code == 401


def test_create_comment(client, app, post, user_headers, normal_user):
    resp = client.post(f'/api/posts/{post.id}/comments', headers=user_headers,
                       json={'content': '不错的一篇文章'})
    assert resp.status_code == 201
    data = resp.get_json()['comment']
    assert data['content'] == '不错的一篇文章'
    assert data['username'] == 'alice'
    assert data['post_id'] == post.id


def test_create_comment_empty_content(client, post, user_headers):
    resp = client.post(f'/api/posts/{post.id}/comments', headers=user_headers,
                       json={'content': '   '})
    assert resp.status_code == 422


def test_create_comment_post_not_found(client, user_headers):
    resp = client.post('/api/posts/9999/comments', headers=user_headers,
                       json={'content': 'hi'})
    assert resp.status_code == 404


# ---------- 评论列表 ----------

def test_list_comments(client, app, post, normal_user):
    _add_comment(post, normal_user, '第一条')
    resp = client.get(f'/api/posts/{post.id}/comments')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['total'] == 1
    assert data['items'][0]['content'] == '第一条'
    assert data['items'][0]['username'] == 'alice'


def test_list_comments_post_not_found(client):
    resp = client.get('/api/posts/9999/comments')
    assert resp.status_code == 404


# ---------- 删除评论（权限） ----------

def test_delete_comment_requires_auth(client, app, post, normal_user):
    c = _add_comment(post, normal_user, '评论')
    resp = client.delete(f'/api/comments/{c.id}')
    assert resp.status_code == 401


def test_delete_comment_forbidden_for_other(client, app, post, normal_user):
    c = _add_comment(post, normal_user, 'alice 的评论')
    _make_user('bob')
    bob_headers = _login_user(client, 'bob', 'secret123')
    resp = client.delete(f'/api/comments/{c.id}', headers=bob_headers)
    assert resp.status_code == 403


def test_delete_comment_by_author(client, app, post, user_headers, normal_user):
    c = _add_comment(post, normal_user, '自己的评论')
    resp = client.delete(f'/api/comments/{c.id}', headers=user_headers)
    assert resp.status_code == 200
    assert db.session.get(Comment, c.id) is None


def test_delete_comment_by_admin(client, app, post, admin_headers, normal_user):
    c = _add_comment(post, normal_user, 'alice 的评论')
    resp = client.delete(f'/api/comments/{c.id}', headers=admin_headers)
    assert resp.status_code == 200
    assert db.session.get(Comment, c.id) is None


def test_delete_comment_not_found(client, user_headers):
    resp = client.delete('/api/comments/9999', headers=user_headers)
    assert resp.status_code == 404
