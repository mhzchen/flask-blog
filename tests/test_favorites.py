"""收藏接口测试：需要登录、收藏/取消收藏、检查、列表"""
from app import db
from app.models import favorites


def _fav_count(post_id, user_id):
    return db.session.query(favorites).filter(
        favorites.c.post_id == post_id, favorites.c.user_id == user_id).count()


def test_list_favorites_requires_auth(client):
    resp = client.get('/api/favorites')
    assert resp.status_code == 401


def test_toggle_on_off(client, post, user_headers, normal_user):
    # 第一次：收藏
    resp = client.post(f'/api/favorites/{post.id}/toggle', headers=user_headers)
    assert resp.status_code == 200
    assert resp.get_json()['favorited'] is True
    assert _fav_count(post.id, normal_user.id) == 1

    # 第二次：取消收藏
    resp = client.post(f'/api/favorites/{post.id}/toggle', headers=user_headers)
    assert resp.status_code == 200
    assert resp.get_json()['favorited'] is False
    assert _fav_count(post.id, normal_user.id) == 0


def test_list_favorites_shows_faved(client, post, user_headers, normal_user):
    client.post(f'/api/favorites/{post.id}/toggle', headers=user_headers)
    resp = client.get('/api/favorites', headers=user_headers)
    data = resp.get_json()
    assert resp.status_code == 200
    assert len(data['items']) == 1
    assert data['items'][0]['id'] == post.id


def test_check_favorite(client, post, user_headers):
    resp = client.get(f'/api/favorites/check/{post.id}', headers=user_headers)
    assert resp.get_json()['favorited'] is False
    client.post(f'/api/favorites/{post.id}/toggle', headers=user_headers)
    resp = client.get(f'/api/favorites/check/{post.id}', headers=user_headers)
    assert resp.get_json()['favorited'] is True


def test_toggle_nonexistent_post(client, user_headers):
    resp = client.post('/api/favorites/9999/toggle', headers=user_headers)
    assert resp.status_code == 404