"""点赞接口测试：需要登录、点赞/取消、like_count、详情 liked、浏览量"""
from app import db
from app.models import post_likes


def _like_count(post_id, user_id):
    return db.session.query(post_likes).filter(
        post_likes.c.post_id == post_id, post_likes.c.user_id == user_id).count()


def test_like_requires_auth(client):
    resp = client.post('/api/v1/posts/1/like')
    assert resp.status_code == 401


def test_toggle_like_on_off(client, post, user_headers, normal_user):
    resp = client.post(f'/api/v1/posts/{post.id}/like', headers=user_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['liked'] is True
    assert data['like_count'] == 1
    assert _like_count(post.id, normal_user.id) == 1

    resp = client.post(f'/api/v1/posts/{post.id}/like', headers=user_headers)
    data = resp.get_json()
    assert data['liked'] is False
    assert data['like_count'] == 0
    assert _like_count(post.id, normal_user.id) == 0


def test_detail_liked_field(client, post, user_headers):
    resp = client.get(f'/api/v1/posts/{post.id}')
    assert resp.get_json()['post']['liked'] is False
    client.post(f'/api/v1/posts/{post.id}/like', headers=user_headers)
    resp = client.get(f'/api/v1/posts/{post.id}', headers=user_headers)
    assert resp.get_json()['post']['liked'] is True
    assert resp.get_json()['post']['like_count'] == 1


def test_detail_has_views(client, post):
    resp = client.get(f'/api/v1/posts/{post.id}')
    assert 'views' in resp.get_json()['post']


def test_like_nonexistent_post(client, user_headers):
    resp = client.post('/api/v1/posts/9999/like', headers=user_headers)
    assert resp.status_code == 404
