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


def test_record_post_view_degrades_without_redis(app, monkeypatch):
    # 测试环境没有 Redis，走降级分支，不抛错；mock DB 避免空库 get 触发重试
    from app.tasks import record_post_view
    from app.models import db
    with app.app_context():
        _stub_post_get(db, monkeypatch)
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
    from app.tasks import enqueue
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



class _FakePost:
    """带 views 属性的假文章对象，避免测试依赖真实 DB schema 状态。"""
    def __init__(self):
        self.views = 0


def _stub_post_get(db, monkeypatch):
    """mock db.session.get 返回一个假文章，完全不碰真实数据库。"""
    fake = _FakePost()
    monkeypatch.setattr(db.session, "get", lambda *a, **k: fake)
    return fake


def test_record_post_view_retries_on_db_error(app, monkeypatch):
    """DB 瞬时连接错误应触发指数退避重试（self.retry），而非直接丢弃。"""
    from app import tasks
    from sqlalchemy.exc import OperationalError
    from app.models import db

    with app.app_context():
        _stub_post_get(db, monkeypatch)

        def boom():
            raise OperationalError("SELECT", {}, Exception("conn lost"))
        monkeypatch.setattr(db.session, "commit", boom)
        retry_called = {"n": 0}

        def fake_retry(exc=None, **kwargs):
            retry_called["n"] += 1
            # 模拟 Celery 抛出 Retry 终止当前执行（真实环境下重试会重新投递）
            raise RuntimeError("retry-issued")

        monkeypatch.setattr(tasks.record_post_view, "retry", fake_retry)
        try:
            tasks.record_post_view(999)
        except RuntimeError:
            pass
        assert retry_called["n"] == 1  # 瞬时错误触发了一次重试


def test_record_post_view_no_retry_on_logic_error(app, monkeypatch):
    """永久错误（非连接类）不重试，直接记日志丢弃（避免无限重试）。"""
    from app import tasks
    from app.models import db

    with app.app_context():
        _stub_post_get(db, monkeypatch)

        def boom():
            raise ValueError("logic bug")
        monkeypatch.setattr(db.session, "commit", boom)
        retry_called = {"n": 0}

        def fake_retry(exc=None, **kwargs):
            retry_called["n"] += 1
            raise RuntimeError("retry-issued")

        monkeypatch.setattr(tasks.record_post_view, "retry", fake_retry)
        tasks.record_post_view(999)
        assert retry_called["n"] == 0  # 永久错误不重试
