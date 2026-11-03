"""限流防刷测试（使用独立 app，开启限流）。

现有 conftest 里 RATELIMIT_ENABLED=False 以免互相干扰，
本文件单独启用限流验证 429 返回。
"""

from app import create_app, db
from app.models import User
from sqlalchemy.pool import StaticPool


def _make_app():
    class RLConfig:
        TESTING = True
        SQLALCHEMY_DATABASE_URI = 'sqlite://'
        SQLALCHEMY_TRACK_MODIFICATIONS = False
        SQLALCHEMY_ENGINE_OPTIONS = {'poolclass': StaticPool, 'connect_args': {'check_same_thread': False}}
        SECRET_KEY = 'test-rl-secret'
        JWT_SECRET_KEY = 'test-rl-jwt'
        CACHE_ENABLED = False
        CELERY_TASK_ALWAYS_EAGER = True
        RATELIMIT_ENABLED = True
        RATELIMIT_STORAGE_URI = 'memory://'
    return create_app(RLConfig)


def test_login_rate_limit_returns_429():
    app = _make_app()
    with app.app_context():
        db.create_all()
        u = User(username='bob', email='bob@example.com')
        u.set_password('secret123')
        db.session.add(u)
        db.session.commit()
    client = app.test_client()
    codes = []
    for _ in range(11):
        resp = client.post('/api/v1/auth/login', json={'username': 'bob', 'password': 'wrong'})
        codes.append(resp.status_code)
    assert codes[-1] == 429


def test_register_rate_limit_returns_429():
    app = _make_app()
    with app.app_context():
        db.create_all()
    client = app.test_client()
    codes = []
    for _ in range(6):
        resp = client.post('/api/v1/auth/register', json={
            'username': f'u{_}', 'email': f'u{_}@e.com', 'password': 'secret123'})
        codes.append(resp.status_code)
    assert codes[-1] == 429
