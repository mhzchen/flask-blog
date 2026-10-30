"""统一 JSON 错误处理 + 请求 ID 中间件测试。"""
import pytest


def test_404_returns_json(client):
    resp = client.get('/api/no-such-route')
    assert resp.status_code == 404
    data = resp.get_json()
    assert data['code'] == 404
    assert 'error' in data
    assert resp.headers.get('X-Request-Id')


def test_405_returns_json(client):
    # /api/categories 只支持 GET，DELETE 触发 405
    resp = client.delete('/api/categories')
    assert resp.status_code == 405
    assert resp.get_json()['code'] == 405


def test_unhandled_exception_returns_500_json_without_detail(app, client):
    @app.get('/boom')
    def boom():
        raise RuntimeError('boom')
    resp = client.get('/boom')
    assert resp.status_code == 500
    data = resp.get_json()
    assert data['code'] == 500
    assert data['error'] == '服务器内部错误'
    # 生产环境（非 debug）不泄露堆栈细节
    assert 'detail' not in data


def test_every_response_has_request_id(client):
    for path in ('/api/posts', '/api/categories', '/api/no-such'):
        resp = client.get(path)
        assert resp.headers.get('X-Request-Id')