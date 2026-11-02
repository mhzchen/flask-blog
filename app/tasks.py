"""Celery 异步任务定义。

任务里通过 current_app / db 访问应用状态（因为任务在应用上下文里执行）。
"""
import socket

from flask import current_app

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


def enqueue(task, *args, **kwargs):
    """安全地投递任务。

    - broker（Redis）可达：异步投递，不阻塞请求；
    - broker 不可达：先探测（1s），不可用则降级为【同步执行】任务本身（功能不丢），
      绝不因异步通道故障拖慢请求（曾出现 Redis 未启动时阻塞 109 秒的问题）。
    """
    # 任何异常都不得抛给请求方（异步通道故障、任务本身报错均吞掉并记日志）
    try:
        # 测试环境已开 eager：直接同步执行；生产走真实 broker
        if celery.conf.get('task_always_eager', False):
            return task.run(*args, **kwargs)
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
    from app.models import db, User
    user = db.session.get(User, user_id)
    if user is None:
        return f'user {user_id} not found'
    current_app.logger.info('[异步任务] 给 %s 发送欢迎邮件', user.email)
    return f'welcome email sent to {user.email}'


@celery.task(name='tasks.record_post_view')
def record_post_view(post_id):
    """异步累加文章浏览量（落库持久化，避免阻塞请求）。"""
    try:
        from app.models import db, Post
        post = db.session.get(Post, post_id)
        if post:
            post.views = (post.views or 0) + 1
            db.session.commit()
    except Exception:
        current_app.logger.warning('浏览计数落库失败: post=%s', post_id, exc_info=True)
    return f'views recorded for post {post_id}'


@celery.task(name='tasks.periodic_ping')
def periodic_ping():
    """定时心跳任务（由 Celery Beat 每分钟触发），演示周期调度。"""
    current_app.logger.info('[周期任务] heartbeat at %s', current_app.config.get('SECRET_KEY', ''))
    return 'pong'
