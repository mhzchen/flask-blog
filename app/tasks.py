"""Celery 异步任务定义。

任务里通过 current_app / db 访问应用状态（因为任务在应用上下文里执行）。
"""
from flask import current_app
from redis import Redis
from redis.exceptions import RedisError

from app.celery_app import celery


def enqueue(task, *args, **kwargs):
    """安全地投递任务：broker 不可用时记录告警，不让请求失败。"""
    try:
        task.delay(*args, **kwargs)
    except Exception:
        current_app.logger.warning('任务投递失败: %s', task.name, exc_info=True)


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
    """异步记录文章浏览量（写 Redis 计数器，避免阻塞请求）。"""
    try:
        client = Redis.from_url(current_app.config['CACHE_REDIS_URL'])
        key = f'post:views:{post_id}'
        client.incr(key)
        client.expire(key, 86400)  # 24h 后自动过期
    except RedisError:
        current_app.logger.warning('浏览计数写入 Redis 失败: post=%s', post_id)
    return f'views recorded for post {post_id}'


@celery.task(name='tasks.periodic_ping')
def periodic_ping():
    """定时心跳任务（由 Celery Beat 每分钟触发），演示周期调度。"""
    current_app.logger.info('[周期任务] heartbeat at %s', current_app.config.get('SECRET_KEY', ''))
    return 'pong'