# -*- coding: utf-8 -*-
"""Meilisearch 全文搜索集成（#56）+ 统一降级观测（#58）。

- 索引：文章发布/更新/删除时通过 Celery 异步同步到 Meilisearch；
- 搜索：GET /api/v1/posts?q= 优先走 Meilisearch 得 post_id 集合，再按 id 查库；
- 降级：Meilisearch 未配置/不可用时回退 MySQL FULLTEXT / SQLite LIKE（原有逻辑），
  且异常统一经 app.degradation.degrade('meilisearch') 记录（可观测，见 /system/degradations）。

所有对外函数对异常"静默降级"，绝不把搜索依赖拖成业务故障点。
"""
import os
from typing import List, Optional

from meilisearch import Client

from app.degradation import degrade

MEILI_INDEX = "posts"


def _client() -> Optional[Client]:
    """惰性构造 Meilisearch 客户端；未配置 master key 时返回 None（走降级搜索）。"""
    url = os.environ.get("MEILI_URL", "http://localhost:7700")
    key = os.environ.get("MEILI_MASTER_KEY", "")
    if not key:
        return None
    try:
        return Client(url, key)
    except Exception as e:
        degrade('meilisearch', 'client init failed: %s' % e)
        return None


def index_post(post_id: int, title: str, summary: str, content: str) -> bool:
    """把一篇文章写入 Meilisearch 索引（不存在则建，存在则更新）。失败返回 False。"""
    client = _client()
    if client is None:
        return False
    try:
        client.index(MEILI_INDEX).add_documents([{
            "id": post_id,
            "title": title,
            "summary": summary,
            "content": content,
        }])
        return True
    except Exception as e:
        degrade('meilisearch', 'index_post failed: %s' % e)
        return False


def unindex_post(post_id: int) -> bool:
    """从 Meilisearch 索引删除一篇文档。失败返回 False。"""
    client = _client()
    if client is None:
        return False
    try:
        client.index(MEILI_INDEX).delete_document(post_id)
        return True
    except Exception as e:
        degrade('meilisearch', 'unindex_post failed: %s' % e)
        return False


def search_post_ids(query: str, limit: int = 200) -> Optional[List[int]]:
    """返回 Meilisearch 命中的 post_id 列表；None 表示 Meilisearch 不可用（调用方应降级）。"""
    client = _client()
    if client is None:
        return None
    try:
        res = client.index(MEILI_INDEX).search(query, {"limit": limit})
        return [int(h["id"]) for h in res.get("hits", [])]
    except Exception as e:
        degrade('meilisearch', 'search failed: %s' % e)
        return None
