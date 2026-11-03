# -*- coding: utf-8 -*-
"""接口幂等性：POST 写接口用 Idempotency-Key 防重复提交。

原理：客户端每次写操作生成唯一 key 放请求头 Idempotency-Key；
服务端把"首次成功响应(status+body)"缓存到 Redis（TTL 默认 24h），
同 key 的后续请求直接返回缓存结果，业务只执行一次（防重放/重复提交）。
Redis 不可用时降级为直接执行（幂等是可靠层，绝不拖垮业务）。
"""
import json
from functools import wraps

from flask import current_app, g, request
from redis.exceptions import RedisError

from app.cache import _client


def _normalize_response(resp):
    """把 Flask 视图返回值统一成 (body_text, status_code)。

    视图可能返回 Response（有 get_data）或 (Response/dict, status) 元组。
    """
    if isinstance(resp, tuple):
        body, status = resp
        code = int(status) if status is not None else 200
        if hasattr(body, 'get_data'):
            return body.get_data(as_text=True), code
        return json.dumps(body, ensure_ascii=False), code
    return resp.get_data(as_text=True), resp.status_code


def idempotent(timeout=86400):
    """把写接口变为幂等：带 Idempotency-Key 的重复请求只执行一次业务。

    缓存 scope 到「key + 用户 + 方法 + 路径」，避免跨请求/跨用户碰撞；
    仅缓存 2xx 成功响应；Redis 故障时降级为直接执行。
    """
    def deco(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            key = request.headers.get('Idempotency-Key')
            if not key:
                return fn(*args, **kwargs)
            app = current_app._get_current_object()  # type: ignore[attr-defined]
            client = _client(app)
            if client is None:
                return fn(*args, **kwargs)  # 无 Redis：降级直接执行
            identity = getattr(g, 'jwt_subject', None) or request.remote_addr
            rkey = f"idem:{key}:{request.method}:{request.path}:{identity}"
            try:
                hit = client.get(rkey)
                if hit is not None:
                    payload = json.loads(hit)
                    return app.response_class(payload['body'], status=payload['status'],
                                               mimetype='application/json')
                resp = fn(*args, **kwargs)
                body_text, code = _normalize_response(resp)
                if 200 <= code < 300:
                    client.setex(rkey, timeout, json.dumps({
                        'status': code,
                        'body': body_text,
                    }))
                return resp
            except (RedisError, ValueError):
                return fn(*args, **kwargs)
        return wrapper
    return deco
