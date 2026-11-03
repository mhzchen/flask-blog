# -*- coding: utf-8 -*-
"""#55 契约测试：OpenAPI 声明的每个 path+method 都能在 Flask 路由匹配。

防止"文档写了但路由没注册"或"路由改了文档没更新"的脱节。
"""
import pytest
from werkzeug.exceptions import NotFound, MethodNotAllowed

from app import create_app
from app.openapi import build_openapi_spec
from config import TestingConfig


@pytest.fixture(scope='module')
def spec():
    return build_openapi_spec()


@pytest.fixture(scope='module')
def app():
    return create_app(TestingConfig)


def _route_paths(app):
    """把 Flask url_map 的规则转成 OpenAPI 形式：/api/v1/posts/<int:post_id> -> /api/v1/posts/{post_id}。"""
    import re
    paths = {}
    for rule in app.url_map.iter_rules():
        if not rule.rule.startswith('/api/'):
            continue
        p = re.sub(r'<[^>:]*:([^>]*)>', r'{\1}', rule.rule)
        paths.setdefault(p, set()).update(rule.methods - {'HEAD', 'OPTIONS'})
    return paths


def test_every_openapi_path_and_method_is_registered(spec, app):
    """OpenAPI PATHS 里每个 path+method 都能在 Flask 路由注册（无缺失）。"""
    routes = _route_paths(app)
    for path, methods in spec['paths'].items():
        assert path in routes, f'OpenAPI {path} 未在 Flask 路由注册'
        for method in methods:
            assert method.upper() in routes[path], f'OpenAPI {method.upper()} {path} 未在 Flask 路由注册'


def test_openapi_has_versioned_paths(spec):
    """接口版本化：#51 后所有路径都带 /api/v1 前缀。"""
    assert spec['paths'], 'OpenAPI 不应为空'
    for path in spec['paths']:
        assert path.startswith('/api/v1/'), f'{path} 缺少 /api/v1 前缀'