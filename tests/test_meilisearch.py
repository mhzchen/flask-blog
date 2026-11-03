# -*- coding: utf-8 -*-
"""#56 Meilisearch 全文搜索：客户端降级 + 列表搜索短路。"""


def test_meili_client_degrades_without_key(monkeypatch):
    """未配置 MEILI_MASTER_KEY 时：索引/搜索/删除全部走降级（不抛错）。"""
    monkeypatch.setenv('MEILI_MASTER_KEY', '')
    from app.meilisearch_client import _client, index_post, search_post_ids, unindex_post
    assert _client() is None
    assert index_post(1, 't', 's', 'c') is False
    assert search_post_ids('q') is None
    assert unindex_post(1) is False


def test_search_uses_meili_ids(monkeypatch, client, post):
    """keyword 时 Meilisearch 返回命中 id 集合 -> 列表按 id 过滤。"""
    monkeypatch.setattr(
        'app.meilisearch_client.search_post_ids', lambda q, limit=200: [post.id])
    r = client.get('/api/v1/posts', query_string={'q': '独家关键词'})
    assert r.status_code == 200
    ids = [i['id'] for i in r.get_json()['items']]
    assert post.id in ids


def test_search_meili_empty_returns_nothing(monkeypatch, client, post):
    """Meilisearch 无命中 -> 返回空列表（不再回退 DB 扫全表）。"""
    monkeypatch.setattr(
        'app.meilisearch_client.search_post_ids', lambda q, limit=200: [])
    r = client.get('/api/v1/posts', query_string={'q': 'xyz-no-hit'})
    assert r.status_code == 200
    assert r.get_json()['items'] == []


def test_search_degrades_to_db_without_meili(client, post):
    """Meilisearch 不可用（search_post_ids 返回 None）-> 降级回 DB 检索，接口仍正常。"""
    r = client.get('/api/v1/posts', query_string={'q': 'python'})
    assert r.status_code == 200



def test_meili_connection_error_returns_false(monkeypatch):
    """已配置 key 但服务不可达：索引/搜索/删除全部降级返回，不抛错。"""
    monkeypatch.setenv('MEILI_MASTER_KEY', 'k')
    import app.meilisearch_client as m

    class _Idx:
        def add_documents(self, docs): raise ConnectionError('meili down')
        def delete_document(self, i): raise ConnectionError('meili down')
        def search(self, q, opts): raise ConnectionError('meili down')

    class _Boom:
        def index(self, name): return _Idx()

    monkeypatch.setattr(m, '_client', lambda: _Boom())
    assert m.index_post(1, 't', 's', 'c') is False
    assert m.search_post_ids('q') is None
    assert m.unindex_post(1) is False



def test_meili_index_success(monkeypatch):
    """Meilisearch 可用：index_post 成功返回 True。"""
    monkeypatch.setenv('MEILI_MASTER_KEY', 'k')
    import app.meilisearch_client as m

    class _Idx:
        def add_documents(self, docs):
            pass

    class _C:
        def index(self, name):
            return _Idx()

    monkeypatch.setattr(m, '_client', lambda: _C())
    assert m.index_post(1, 't', 's', 'c') is True


def test_meili_unindex_success(monkeypatch):
    """Meilisearch 可用：unindex_post 成功返回 True。"""
    monkeypatch.setenv('MEILI_MASTER_KEY', 'k')
    import app.meilisearch_client as m

    class _Idx:
        def delete_document(self, i):
            pass

    class _C:
        def index(self, name):
            return _Idx()

    monkeypatch.setattr(m, '_client', lambda: _C())
    assert m.unindex_post(1) is True



def test_meili_search_success(monkeypatch):
    """Meilisearch 可用：search_post_ids 返回命中 id 列表。"""
    monkeypatch.setenv('MEILI_MASTER_KEY', 'k')
    import app.meilisearch_client as m

    class _Idx:
        def search(self, q, opts):
            return {'hits': [{'id': 1}, {'id': 2}]}

    class _C:
        def index(self, name):
            return _Idx()

    monkeypatch.setattr(m, '_client', lambda: _C())
    assert m.search_post_ids('q') == [1, 2]
