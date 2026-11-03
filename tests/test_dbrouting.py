"""SQLAlchemy 读写分离 RoutingSession 路由逻辑测试（mock engines，不触真实库）。"""
from app.dbrouting import RoutingSession


class _FakeSA:
    """伪造 SQLAlchemy 扩展，仅暴露 engines 映射（None=主库，slave=从库）。"""
    def __init__(self, engines):
        self.engines = engines


def _session(engines, app, monkeypatch):
    monkeypatch.setitem(app.extensions, 'sqlalchemy', _FakeSA(engines))
    sess = object.__new__(RoutingSession)
    return sess


def test_read_goes_slave_when_configured(app, monkeypatch):
    """配置了 slave 时，非 flush 的普通读查询走从库引擎。"""
    with app.app_context():
        sess = _session({None: 'master', 'slave': 'slave'}, app, monkeypatch)
        sess._flushing = False
        assert sess.get_bind() == 'slave'


def test_write_goes_master_always(app, monkeypatch):
    """flush/commit（写）固定走主库引擎，即便配置了从库。"""
    with app.app_context():
        sess = _session({None: 'master', 'slave': 'slave'}, app, monkeypatch)
        sess._flushing = True
        assert sess.get_bind() == 'master'


def test_read_falls_back_master_without_slave(app, monkeypatch):
    """未配置 slave（dev/SQLite/测试）时，读查询回落主库，行为与单库一致。"""
    with app.app_context():
        sess = _session({None: 'master'}, app, monkeypatch)
        sess._flushing = False
        assert sess.get_bind() == 'master'
