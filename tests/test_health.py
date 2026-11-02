"""健康检查测试：/health 存活探针、/healthz 就绪探针（含 DB 依赖检查）"""
def test_health(client):
    resp = client.get('/health')
    assert resp.status_code == 200
    assert resp.get_json()['status'] == 'ok'


def test_healthz_ok(client):
    resp = client.get('/healthz')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['status'] == 'ok'
    assert data['checks']['database'] == 'ok'
