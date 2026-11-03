# -*- coding: utf-8 -*-
"""#56 索引任务：Meilisearch 索引/移除任务（eager 同步执行路径）。"""


def test_index_post_search_task(client, post, monkeypatch):
    """index_post_search：文章索引到 Meilisearch（eager 直接 run）。"""
    import app.meilisearch_client as m
    from app.tasks import enqueue, index_post_search

    calls = {}
    monkeypatch.setattr(
        m, 'index_post', lambda pid, t, s, c: calls.update({'pid': pid, 't': t}) or True)
    enqueue(index_post_search, post.id)
    assert calls.get('pid') == post.id


def test_index_post_search_missing_post(client, post, monkeypatch):
    """index_post_search：文章不存在时安全返回（不报错）。"""
    import app.meilisearch_client as m
    from app.tasks import index_post_search

    monkeypatch.setattr(m, 'index_post', lambda *a, **k: True)
    r = index_post_search.run(999999999)
    assert 'not found' in r


def test_unindex_post_search_task(client, post, monkeypatch):
    """unindex_post_search：从 Meilisearch 移除文档。"""
    import app.meilisearch_client as m
    from app.tasks import enqueue, unindex_post_search

    calls = {}
    monkeypatch.setattr(
        m, 'unindex_post', lambda pid: calls.update({'pid': pid}) or True)
    enqueue(unindex_post_search, post.id)
    assert calls.get('pid') == post.id
