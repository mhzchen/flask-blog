"""Celery 异步任务定义。

任务里通过 current_app / db 访问应用状态（因为任务在应用上下文里执行）。
"""
import json
import socket
import time

from flask import current_app

from app import cache
from app.celery_app import celery


def _broker_reachable(timeout=1.0):
    """快速探测 broker（Redis）是否可达。不可达返回 False，避免 task.delay 阻塞重试。"""
    try:
        from urllib.parse import urlparse
        url = celery.conf.get('broker_url', 'redis://localhost:6379/1')
        parts = urlparse(url)
        host = parts.hostname or 'localhost'
        port = parts.port or 6379
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False


def _view_dedup(app, post_id):
    """record_post_view 投递去重：同一 post 短窗口只投递一次（防前端重试/网络重发重复计数）。

    用 Redis SETNX 原子占位，TTL 窗口内重复投递直接跳过；Redis 不可用降级为照常投递（不丢）。
    """
    client = cache._client(app)
    if client is None:
        return False
    try:
        return not client.set(f'view_dedup:{post_id}', '1', nx=True, ex=120)
    except Exception:
        return False


def _record_deadletter(app, task_name, args, error):
    """重试耗尽仍失败的永久错误进死信（Redis list），供运维追溯。"""
    client = cache._client(app)
    if client is None:
        return
    try:
        client.lpush('task_deadletter', json.dumps({
            'task': task_name, 'args': args, 'error': error, 'ts': round(time.time(), 3),
        }, ensure_ascii=False))
    except Exception:
        pass


def enqueue(task, *args, **kwargs):
    """安全地投递任务。

    - broker（Redis）可达：异步投递，不阻塞请求；
    - broker 不可达：先探测（1s），不可用则降级为【同步执行】任务本身（功能不丢），
      绝不因异步通道故障拖慢请求（曾出现 Redis 未启动时阻塞 109 秒的问题）。
    - record_post_view 幂等去重：同一 post 短窗口只投递一次。
    """
    # 任何异常都不得抛给请求方（异步通道故障、任务本身报错均吞掉并记日志）
    try:
        # 测试环境已开 eager：直接同步执行；生产走真实 broker
        if celery.conf.get('task_always_eager', False):
            return task.run(*args, **kwargs)
        # record_post_view 投递去重（窗口内已投递则跳过，避免重复计数）
        if task.name == 'tasks.record_post_view' and args and _view_dedup(current_app._get_current_object(), args[0]):
            return None
        # broker 不可达时不投递，直接降级同步执行
        if not _broker_reachable():
            current_app.logger.warning(
                'broker 不可达，降级为同步执行: %s', task.name)
            return task.run(*args, **kwargs)
        task.delay(*args, **kwargs)
    except Exception:
        # broker 故障或任务同步执行报错：降级尝试同步执行，仍失败则只记日志
        current_app.logger.warning('任务投递失败: %s', task.name, exc_info=True)
        try:
            return task.run(*args, **kwargs)
        except Exception:
            current_app.logger.warning('任务同步执行也失败: %s', task.name, exc_info=True)


@celery.task(name='tasks.send_welcome_email')
def send_welcome_email(user_id):
    """注册后异步发送欢迎邮件（此处模拟，真实项目换成 SMTP/邮件服务）。"""
    from app.models import User, db
    user = db.session.get(User, user_id)
    if user is None:
        return f'user {user_id} not found'
    current_app.logger.info('[异步任务] 给 %s 发送欢迎邮件', user.email)
    return f'welcome email sent to {user.email}'


@celery.task(name='tasks.record_post_view', bind=True, max_retries=3)
def record_post_view(self, post_id):
    """异步累加文章浏览量（落库持久化，避免阻塞请求）。

    可靠性：DB 瞬时连接错误（OperationalError）按指数退避自动重试（2/4/8s，最多 3 次），
    避免一次连接抖动就丢失浏览计数；永久错误（数据/逻辑问题）记日志丢弃，不无限重试。
    """
    from sqlalchemy.exc import OperationalError

    from app.models import Post, db
    try:
        post = db.session.get(Post, post_id)
        if post:
            post.views = (post.views or 0) + 1
            db.session.commit()
    except OperationalError as exc:
        # 瞬时连接错误：回滚后指数退避重试（countdown = 2 ^ retries）
        db.session.rollback()
        if self.request.retries >= self.max_retries:
            # 重试耗尽仍失败：永久错误进死信（可追溯），不再重试，避免无限积压
            _record_deadletter(current_app._get_current_object(), 'record_post_view', [post_id], 'OperationalError')
            current_app.logger.warning('浏览计数重试耗尽，进死信: post=%s', post_id)
            return f'views failed permanently for post {post_id}'
        current_app.logger.warning('浏览计数落库瞬时错误，重试 %s/%s: post=%s',
                                   self.request.retries + 1, self.max_retries, post_id)
        raise self.retry(exc=exc, countdown=2 ** self.request.retries) from exc
    except Exception:
        db.session.rollback()
        current_app.logger.warning('浏览计数落库失败: post=%s', post_id, exc_info=True)
    return f'views recorded for post {post_id}'


@celery.task(name='tasks.periodic_ping')
def periodic_ping():
    """定时心跳任务（由 Celery Beat 每分钟触发），演示周期调度。"""
    current_app.logger.info('[周期任务] heartbeat at %s', current_app.config.get('SECRET_KEY', ''))
    return 'pong'


@celery.task(name='tasks.warm_hot_cache')
def warm_hot_cache():
    """周期预热热点缓存（Celery Beat 每 2 分钟触发）。

    内部请求首页列表与热门文章详情，让 cached 装饰器把响应写进 Redis；
    冷启动/缓存过期后由 beat 提前填充，避免流量高峰瞬时打穿 DB（与防雪崩呼应）。
    """
    import urllib.request

    base = current_app.config.get('BACKEND_INTERNAL_URL', 'http://localhost:8000')
    warmed = 0
    for path in ('/api/posts', '/api/posts/1', '/api/posts/2', '/api/posts/3'):
        try:
            with urllib.request.urlopen(base + path, timeout=5) as resp:
                if resp.status == 200:
                    warmed += 1
        except Exception:
            current_app.logger.warning('[周期任务] 预热失败: %s', path)
    current_app.logger.info('[周期任务] 热点缓存预热完成，命中 %s 条路径', warmed)
    return f'warmed {warmed} paths'


@celery.task(name='tasks.prune_deadletter')
def prune_deadletter():
    """周期清理死信列表（Celery Beat 每小时触发）。

    重试耗尽仍失败的永久错误会进 Redis list `task_deadletter`；
    本任务用 ltrim 只保留最近 DEADLETTER_MAX 条，防止列表无限膨胀。
    """
    app = current_app._get_current_object()
    client = cache._client(app)
    if client is None:
        return 'no cache, skipped'
    limit = int(current_app.config.get('DEADLETTER_MAX', 100))
    try:
        client.ltrim('task_deadletter', 0, limit - 1)
        left = client.llen('task_deadletter') or 0
        current_app.logger.info('[周期任务] 死信清理完成，剩余 %s 条', left)
        return f'pruned, {left} left'
    except Exception:
        current_app.logger.warning('[周期任务] 死信清理失败', exc_info=True)
        return 'prune failed'
