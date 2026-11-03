# -*- coding: utf-8 -*-
"""系统状态 async 视图：演示 Flask 3.x async 路由 + asyncio.gather 并发 I/O 探查。

Flask 3.x 原生支持 async 视图（async def 端点）；本端点用 asyncio.gather + to_thread
并发探查 数据库 / Redis / Celery broker 三项依赖的延迟，展示"一次请求并发 I/O"的写法。
真正并发收益在 ASGI server（如 hypercorn）下体现；gunicorn(WSGI) 下 Flask 会自动桥接、
功能同样可用。
"""
import asyncio
import time

from flask import Blueprint, current_app, jsonify

system_bp = Blueprint('system', __name__)


def _db_probe(app):
    from app import db
    with app.app_context():
        with db.session() as s:
            s.execute(db.text('SELECT 1'))


def _redis_probe(app):
    import redis as redislib
    client = redislib.from_url(app.config.get('CACHE_REDIS_URL', 'redis://localhost:6379/0'))
    try:
        client.ping()
    finally:
        client.close()


def _broker_probe(app):
    import redis as redislib
    client = redislib.from_url(app.config.get('CELERY_BROKER_URL', 'redis://localhost:6379/1'))
    try:
        client.ping()
    finally:
        client.close()


@system_bp.get('/status')
async def system_status():
    """异步并发探查 DB/Redis/Celery broker 延迟（演示 async 视图 + asyncio.gather 并发 I/O）。"""
    app = current_app._get_current_object()
    t0 = time.perf_counter()

    async def probe(name, fn):
        start = time.perf_counter()
        try:
            await asyncio.to_thread(fn, app)
            return {'name': name, 'ok': True, 'ms': round((time.perf_counter() - start) * 1000, 1)}
        except Exception as e:
            return {
                'name': name,
                'ok': False,
                'ms': round((time.perf_counter() - start) * 1000, 1),
                'error': str(e),
            }

    checks = await asyncio.gather(
        probe('database', _db_probe),
        probe('redis', _redis_probe),
        probe('celery_broker', _broker_probe),
    )
    total = round((time.perf_counter() - t0) * 1000, 1)
    return jsonify({
        'async': True,
        'endpoint': '/api/v1/system/status',
        'checks': list(checks),
        'total_ms': total,
    })


@system_bp.get('/degradations')
def system_degradations():
    """统一服务降级状态汇总（#58）：各服务开关 / 累计降级次数 / 最近原因 / 是否降级。

    供运维从单端点观测当前哪些依赖处于降级（配合 degrade() 接入点与 logs 聚合）。
    """
    from app.degradation import degradation_summary
    return jsonify({'degradations': degradation_summary()})
