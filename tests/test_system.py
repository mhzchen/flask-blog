# -*- coding: utf-8 -*-
"""#53 Flask async 视图：/api/v1/system/status 并发探查测试。"""


def test_system_status_returns_async_checks(client):
    """async 视图返回 200 + async 标志 + 三项依赖探查（DB 可通，Redis/broker 视环境）。"""
    resp = client.get('/api/v1/system/status')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['async'] is True
    assert data['endpoint'] == '/api/v1/system/status'
    assert len(data['checks']) == 3
    names = {c['name'] for c in data['checks']}
    assert names == {'database', 'redis', 'celery_broker'}
    db_check = next(c for c in data['checks'] if c['name'] == 'database')
    assert db_check['ok'] is True
    assert 'total_ms' in data


def test_system_status_per_check_fields(client):
    """每项 checks 含 ok/ms 字段。"""
    resp = client.get('/api/v1/system/status')
    data = resp.get_json()
    for check in data['checks']:
        assert 'ok' in check
        assert 'ms' in check
