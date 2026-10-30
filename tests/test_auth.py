"""认证接口测试：注册 / 登录 / 当前用户"""
import pytest


@pytest.fixture()
def reg_payload():
    return {'username': 'bob', 'email': 'bob@example.com', 'password': 'secret123'}


def test_register_success(client, reg_payload):
    resp = client.post('/api/auth/register', json=reg_payload)
    assert resp.status_code == 201
    data = resp.get_json()
    assert 'access_token' in data
    assert data['user']['username'] == 'bob'
    assert data['user']['email'] == 'bob@example.com'


def test_register_missing_fields(client):
    resp = client.post('/api/auth/register', json={})
    assert resp.status_code == 422


def test_register_short_password(client, reg_payload):
    reg_payload['password'] = '123'
    resp = client.post('/api/auth/register', json=reg_payload)
    assert resp.status_code == 422


def test_register_duplicate_username(client, reg_payload):
    client.post('/api/auth/register', json=reg_payload)
    resp = client.post('/api/auth/register', json=reg_payload)
    assert resp.status_code == 409
    assert '用户名已被使用' in resp.get_json()['error']


def test_register_duplicate_email(client, reg_payload):
    client.post('/api/auth/register', json=reg_payload)
    dup = {'username': 'bob2', 'email': 'bob@example.com', 'password': 'secret123'}
    resp = client.post('/api/auth/register', json=dup)
    assert resp.status_code == 409
    assert '邮箱已被注册' in resp.get_json()['error']


def test_login_success(client, normal_user):
    resp = client.post('/api/auth/login',
                       json={'username': 'alice', 'password': 'secret123'})
    assert resp.status_code == 200
    assert 'access_token' in resp.get_json()


def test_login_wrong_password(client, normal_user):
    resp = client.post('/api/auth/login',
                       json={'username': 'alice', 'password': 'wrongpass'})
    assert resp.status_code == 401


def test_login_nonexistent_user(client):
    resp = client.post('/api/auth/login',
                       json={'username': 'nobody', 'password': 'whatever1'})
    assert resp.status_code == 401


def test_me_requires_token(client):
    resp = client.get('/api/auth/me')
    assert resp.status_code == 401


def test_me_success(client, user_headers):
    resp = client.get('/api/auth/me', headers=user_headers)
    assert resp.status_code == 200
    assert resp.get_json()['user']['username'] == 'alice'