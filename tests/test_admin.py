"""后台管理接口测试：权限控制 + 文章/分类增删改"""
import pytest


def test_admin_requires_auth(client):
    resp = client.get('/api/admin/posts')
    assert resp.status_code == 401


def test_admin_forbidden_for_normal_user(client, user_headers):
    resp = client.get('/api/admin/posts', headers=user_headers)
    assert resp.status_code == 403


# ---------- 文章管理 ----------

def test_admin_create_post(client, app, admin_headers, category):
    resp = client.post('/api/admin/posts', headers=admin_headers, json={
        'title': '新文章', 'summary': '摘要', 'content': '正文',
        'category_id': category.id,
    })
    assert resp.status_code == 201
    data = resp.get_json()['post']
    assert data['title'] == '新文章'
    assert data['content'] == '正文'


def test_admin_create_post_missing_title(client, admin_headers, category):
    resp = client.post('/api/admin/posts', headers=admin_headers, json={
        'title': '', 'category_id': category.id,
    })
    assert resp.status_code == 400


def test_admin_create_post_bad_category(client, admin_headers):
    resp = client.post('/api/admin/posts', headers=admin_headers, json={
        'title': 'x', 'category_id': 9999,
    })
    assert resp.status_code == 400


def test_admin_update_post(client, app, admin_headers, category, post):
    resp = client.put(f'/api/admin/posts/{post.id}', headers=admin_headers, json={
        'title': '改标题', 'summary': '新摘要', 'content': '新正文',
        'category_id': category.id,
    })
    assert resp.status_code == 200
    assert resp.get_json()['post']['title'] == '改标题'


def test_admin_delete_post(client, app, admin_headers, post):
    resp = client.delete(f'/api/admin/posts/{post.id}', headers=admin_headers)
    assert resp.status_code == 200
    assert client.get(f'/api/posts/{post.id}').status_code == 404


# ---------- 分类管理 ----------

def test_admin_create_category(client, admin_headers):
    resp = client.post('/api/admin/categories', headers=admin_headers,
                       json={'name': 'Go', 'slug': 'go'})
    assert resp.status_code == 201
    assert resp.get_json()['category']['slug'] == 'go'


def test_admin_create_category_duplicate_slug(client, admin_headers, category):
    resp = client.post('/api/admin/categories', headers=admin_headers,
                       json={'name': '重复', 'slug': 'python'})
    assert resp.status_code == 409


def test_admin_update_category(client, admin_headers, category):
    resp = client.put(f'/api/admin/categories/{category.id}', headers=admin_headers,
                      json={'name': '改名', 'slug': 'renamed'})
    assert resp.status_code == 200
    assert resp.get_json()['category']['name'] == '改名'


def test_admin_delete_category(client, admin_headers, category):
    resp = client.delete(f'/api/admin/categories/{category.id}', headers=admin_headers)
    assert resp.status_code == 200
    assert resp.get_json()['message'] == '分类已删除。'