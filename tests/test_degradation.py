# -*- coding: utf-8 -*-
"""#58 统一服务降级开关测试。"""
import pytest
from app.degradation import _state, degradation_summary, degrade, is_degraded
from flask import Flask


@pytest.fixture(autouse=True)
def _reset_state():
    _state.clear()
    yield
    _state.clear()


def _app():
    a = Flask(__name__)
    a.config['SERVICE_DEGRADATION_ENABLED'] = True
    a.config['DEGRADATION_REDIS_CACHE'] = True
    a.config['DEGRADATION_MEILISEARCH'] = True
    a.config['DEGRADATION_REDIS_JWT'] = True
    a.config['DEGRADATION_REDIS_LOGIN'] = True
    a.config['DEGRADATION_CELERY'] = True
    return a


def test_degrade_records_event_and_summary():
    app = _app()
    degrade('redis_cache', 'redis down', app)
    degrade('redis_cache', 'redis down again', app)
    s = degradation_summary()
    entry = next(x for x in s if x['service'] == 'redis_cache')
    assert entry['count'] == 2
    assert entry['degraded'] is True
    assert entry['last_reason'] == 'redis down again'
    assert is_degraded('redis_cache') is True


def test_degrade_ignores_unknown_service():
    app = _app()
    degrade('not_a_service', 'x', app)
    assert degradation_summary() == []


def test_disabled_total_switch_marks_not_enabled():
    app = _app()
    app.config['SERVICE_DEGRADATION_ENABLED'] = False
    degrade('redis_cache', 'down', app)
    entry = next(x for x in degradation_summary() if x['service'] == 'redis_cache')
    assert entry['enabled'] is False
    assert entry['count'] == 1  # 事件仍被记录（含 enabled=false 供观测）


def test_per_service_switch_disable():
    app = _app()
    app.config['DEGRADATION_MEILISEARCH'] = False
    degrade('meilisearch', 'down', app)
    entry = next(x for x in degradation_summary() if x['service'] == 'meilisearch')
    assert entry['enabled'] is False


def test_wire_meilisearch_search_records_degradation(monkeypatch):
    """meilisearch search 异常 -> degrade('meilisearch') 记录（无请求上下文也计数）。"""
    from app import meilisearch_client

    class _Failing:
        def index(self, _):
            class _I:
                def search(self, *_a, **_k):
                    raise ConnectionError('meili unreachable')
            return _I()

    monkeypatch.setattr(meilisearch_client, '_client', lambda: _Failing())
    _app()
    assert meilisearch_client.search_post_ids('hello') is None
    entry = next(x for x in degradation_summary() if x['service'] == 'meilisearch')
    assert entry['count'] >= 1


def test_system_degradations_endpoint():
    from app import create_app
    app = create_app('testing')
    client = app.test_client()
    resp = client.get('/api/v1/system/degradations')
    assert resp.status_code == 200
    body = resp.get_json()
    assert 'degradations' in body
    assert isinstance(body['degradations'], list)
