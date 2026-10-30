"""Swagger UI / OpenAPI 规范端点测试（含 Pydantic 自动生成 schema）。"""
import pytest


def test_swagger_page(client):
    resp = client.get('/swagger')
    assert resp.status_code == 200
    assert 'Swagger UI' in resp.get_data(as_text=True)


def test_openapi_json_meta(client):
    spec = client.get('/openapi.json').get_json()
    assert spec['openapi'] == '3.0.3'
    assert spec['info']['version'] == '1.1.0'
    for name in ('RegisterBody', 'LoginBody', 'PostBody', 'CategoryBody'):
        assert name in spec['components']['schemas']


def test_openapi_schema_generated_from_pydantic(client):
    reg = client.get('/openapi.json').get_json()['components']['schemas']['RegisterBody']['properties']
    assert reg['username']['maxLength'] == 30
    assert reg['password']['minLength'] == 6
    assert reg['email']['format'] == 'email'