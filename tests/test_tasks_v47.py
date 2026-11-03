"""#47 异步可靠性深化测试：分布式锁 / 死信告警 / 队列路由 / warm 防重入。"""


class _FakeRedis:
    """内存 Redis 替身：支持 set(nx,ex)/lpush/llen/ltrim/delete（锁 + 死信用）。"""
    def __init__(self):
        self.store = {}
        self.ttls = {}

    def set(self, key, val, nx=False, ex=None):
        if nx and key in self.store:
            return False
        self.store[key] = val
        if ex:
            self.ttls[key] = ex
        return True

    def lpush(self, key, val):
        self.store.setdefault(key, []).insert(0, val)
        return 1

    def llen(self, key):
        return len(self.store.get(key, []))

    def ltrim(self, key, start, stop):
        self.store[key] = self.store.get(key, [])[start:stop + 1]

    def delete(self, key):
        self.store.pop(key, None)
        return 1


def test_task_lock_acquired(app):
    """锁未被占用时返回 True，并在 Redis 占位。"""
    from app.tasks import task_lock
    r = _FakeRedis()
    with app.app_context():
        app.extensions['cache_redis'] = r
        assert task_lock('demo') is True
        assert r.store.get('task_lock:demo') == '1'


def test_task_lock_held_returns_false(app):
    """锁已占用（另一 worker 持有）时返回 False，防重入。"""
    from app.tasks import task_lock
    r = _FakeRedis()
    with app.app_context():
        app.extensions['cache_redis'] = r
        assert task_lock('demo') is True
        assert task_lock('demo') is False


def test_task_lock_no_redis_degrades(app):
    """Redis 不可用（cache None）时退化为无锁执行，不阻塞任务。"""
    from app.tasks import task_lock
    with app.app_context():
        app.extensions['cache_redis'] = None
        assert task_lock('demo') is True


def test_send_alert_empty_url_silent(app):
    """无 webhook URL 时静默返回，不抛错。"""
    from app.tasks import _send_alert
    with app.app_context():
        app.config['ALERT_WEBHOOK_URL'] = ''
        _send_alert(app, {'type': 'x'})


def test_send_alert_push_failure_silent(app, monkeypatch):
    """webhook 推送失败静默（告警通道故障不影响任务）。"""
    from app.tasks import _send_alert

    def boom(*a, **k):
        raise RuntimeError('down')
    monkeypatch.setattr('urllib.request.urlopen', boom)
    with app.app_context():
        app.config['ALERT_WEBHOOK_URL'] = 'http://example.com/alerts'
        _send_alert(app, {'type': 'x'})


def test_send_alert_posts_payload(app, monkeypatch):
    """webhook 收到正确的告警载荷。"""
    from app.tasks import _send_alert
    sent = {}

    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def fake_urlopen(req, timeout=3):
        sent['url'] = req.full_url
        sent['body'] = req.data
        return _Resp()
    monkeypatch.setattr('urllib.request.urlopen', fake_urlopen)
    with app.app_context():
        app.config['ALERT_WEBHOOK_URL'] = 'http://example.com/alerts'
        _send_alert(app, {'type': 'deadletter_high', 'error': 'boom'})
    assert sent['url'] == 'http://example.com/alerts'
    assert b'deadletter_high' in sent['body']


def test_warm_hot_cache_skips_when_lock_held(app):
    """warm_hot_cache 锁被占（另一 worker 预热中）时跳过本次，防重入。"""
    from app import tasks
    r = _FakeRedis()
    with app.app_context():
        app.extensions['cache_redis'] = r
        r.store['task_lock:warm_hot_cache'] = '1'
        assert tasks.warm_hot_cache() == 'skipped (lock held)'


def test_prune_deadletter_alerts_over_threshold(app, monkeypatch):
    """死信超过阈值（>=80%）时触发 _send_alert 运维告警。"""
    from app import tasks
    r = _FakeRedis()
    monkeypatch.setattr(tasks.cache, '_client', lambda app: r)
    with app.app_context():
        app.config['DEADLETTER_MAX'] = 10
        for _ in range(9):
            r.lpush('task_deadletter', 'x')
        alerted = []

        def fake_send(a, payload):
            alerted.append(payload)
        monkeypatch.setattr(tasks, '_send_alert', fake_send)
        res = tasks.prune_deadletter()
        assert 'pruned' in res
        assert alerted and alerted[0]['type'] == 'deadletter_high'


def test_prune_deadletter_no_alert_below_threshold(app, monkeypatch):
    """死信低于阈值时不发告警。"""
    from app import tasks
    r = _FakeRedis()
    monkeypatch.setattr(tasks.cache, '_client', lambda app: r)
    with app.app_context():
        app.config['DEADLETTER_MAX'] = 10
        for _ in range(3):
            r.lpush('task_deadletter', 'x')
        alerted = []

        def fake_send(a, payload):
            alerted.append(payload)
        monkeypatch.setattr(tasks, '_send_alert', fake_send)
        tasks.prune_deadletter()
        assert alerted == []


def test_task_routes_critical_queue(app):
    """维护类任务（预热/死信清理）路由到 critical 队列，与 default 隔离。"""
    from app.celery_app import celery
    routes = celery.conf.get('task_routes', {})
    assert routes.get('tasks.warm_hot_cache', {}).get('queue') == 'critical'
    assert routes.get('tasks.prune_deadletter', {}).get('queue') == 'critical'
