"""pytest 全局配置与测试夹具。

测试使用内存版 SQLite（StaticPool 保证同库共享），与 MySQL 完全隔离。
测试里禁用 Redis 缓存，并让 Celery 以 eager 模式同步执行，
因此无需启动 Redis / Worker 也能跑通全部用例。
"""
import pytest
from sqlalchemy.pool import StaticPool

from app import create_app, db
from app.models import User, Category, Post


class TestConfig:
    """测试专用配置：覆盖默认配置，改用内存 SQLite，禁用缓存与异步 broker"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite://'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'poolclass': StaticPool,
        'connect_args': {'check_same_thread': False},
    }
    SECRET_KEY = 'test-secret-key-0123456789abcdef'
    JWT_SECRET_KEY = 'test-jwt-secret-key-0123456789abcdef'
    JWT_ACCESS_TOKEN_EXPIRES = 3600
    CORS_ORIGINS = '*'

    # 测试不需要 Redis：关掉缓存，Celery 走 eager 同步执行
    CACHE_ENABLED = False
    CACHE_REDIS_URL = 'redis://localhost:6379/0'
    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_TASK_EAGER_PROPAGATES = True
    CELERY_BROKER_URL = 'memory://'
    CELERY_RESULT_BACKEND = 'cache+memory://'


@pytest.fixture()
def app():
    """每个测试独立的应用实例 + 全新建表，测试之间互不干扰。

    上下文在整个测试期间保持打开，yield 结束后统一清库。
    """
    application = create_app(TestConfig)
    with application.app_context():
        db.create_all()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    """测试用 HTTP 客户端（无需真正起服务器）"""
    return app.test_client()


# ---------------- 数据工厂夹具 ----------------

@pytest.fixture()
def normal_user():
    u = User(username='alice', email='alice@example.com')
    u.set_password('secret123')
    db.session.add(u)
    db.session.commit()
    return u


@pytest.fixture()
def admin_user():
    u = User(username='admin', email='admin@example.com', is_admin=True)
    u.set_password('secret123')
    db.session.add(u)
    db.session.commit()
    return u


@pytest.fixture()
def category():
    c = Category(name='Python', slug='python')
    db.session.add(c)
    db.session.commit()
    return c


@pytest.fixture()
def post(category):
    p = Post(title='Hello Flask', slug='hello-flask',
             summary='测试摘要', content='<p>测试正文</p>',
             category_id=category.id)
    db.session.add(p)
    db.session.commit()
    return p


def _login(client, username, password):
    """登录并返回带 token 的请求头"""
    resp = client.post('/api/auth/login',
                       json={'username': username, 'password': password})
    assert resp.status_code == 200, resp.get_json()
    token = resp.get_json()['access_token']
    return {'Authorization': f'Bearer {token}'}


@pytest.fixture()
def user_headers(client, normal_user):
    return _login(client, 'alice', 'secret123')


@pytest.fixture()
def admin_headers(client, admin_user):
    return _login(client, 'admin', 'secret123')