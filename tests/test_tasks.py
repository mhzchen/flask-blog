"""Celery 异步任务与安全投递测试（eager 模式同步执行，不依赖外部服务）。"""


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

def test_broker_reachable_returns_false_when_down(app, monkeypatch):
    """broker(Redis) 未启动时，探测应快速返回 False（不阻塞）。"""
    from app.tasks import _broker_reachable
    def fake_connect(addr, timeout=1.0):
        raise ConnectionRefusedError('redis down')
    monkeypatch.setattr('app.tasks.socket.create_connection', fake_connect)
    assert _broker_reachable() is False


def test_enqueue_degrades_to_sync_when_broker_down(app, monkeypatch):
    """broker 不可达且非 eager 时，enqueue 降级为同步执行任务本体。"""
    from app.tasks import enqueue, _broker_reachable
    monkeypatch.setattr('app.tasks.celery.conf', {'task_always_eager': False})
    monkeypatch.setattr('app.tasks._broker_reachable', lambda timeout=1.0: False)
    class FakeTask:
        name = 'fake.task'
        def run(self, *args, **kwargs):
            return 'ran-sync'
    with app.app_context():
        assert enqueue(FakeTask()) == 'ran-sync'


def test_enqueue_eager_runs_sync(app, monkeypatch):
    """eager 模式下 enqueue 直接同步执行，不碰 broker。"""
    from app.tasks import enqueue
    monkeypatch.setattr('app.tasks.celery.conf', {'task_always_eager': True})
    class FakeTask:
        name = 'fake.task'
        def run(self, *args, **kwargs):
            return 'eager-sync'
    with app.app_context():
        assert enqueue(FakeTask()) == 'eager-sync'

