"""Celery 异步任务与安全投递测试（eager 模式同步执行，不依赖外部服务）。"""
import pytest


def test_periodic_ping(app):
    from app.tasks import periodic_ping
    with app.app_context():
        assert periodic_ping() == 'pong'


def test_send_welcome_email_existing(app, normal_user):
    from app.tasks import send_welcome_email
    with app.app_context():
        assert 'sent to' in send_welcome_email.run(normal_user.id)


def test_send_welcome_email_missing_user(app):
    from app.tasks import send_welcome_email
    with app.app_context():
        assert send_welcome_email.run(99999) == 'user 99999 not found'


def test_record_post_view_degrades_without_redis(app):
    # 测试环境没有 Redis，走降级分支，不抛错
    from app.tasks import record_post_view
    with app.app_context():
        assert record_post_view(1) == 'views recorded for post 1'


def test_enqueue_swallows_broker_error(app):
    from app.tasks import enqueue
    class BrokenTask:
        name = 'broken.task'
        def delay(self, *args, **kwargs):
            raise RuntimeError('broker down')
    # broker 故障时不应抛给调用方
    with app.app_context():
        enqueue(BrokenTask())