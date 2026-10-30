"""OpenAPI 3.0 接口文档规范 + Swagger UI 页面。

- GET /openapi.json  -> 返回 OpenAPI 3.0 规范（Swagger UI 的数据源）
- GET /swagger       -> Swagger UI 页面（在线渲染接口文档）
"""
from flask import jsonify

# 数据模型（组件复用）
SCHEMAS = {
    "RegisterBody": {
        "type": "object",
        "required": ["username", "email", "password"],
        "properties": {
            "username": {"type": "string", "minLength": 1, "maxLength": 30, "description": "用户名"},
            "email": {"type": "string", "format": "email", "description": "邮箱"},
            "password": {"type": "string", "minLength": 6, "description": "密码，至少 6 位"},
        },
    },
    "LoginBody": {
        "type": "object",
        "required": ["username", "password"],
        "properties": {
            "username": {"type": "string", "minLength": 1, "description": "用户名"},
            "password": {"type": "string", "minLength": 1, "description": "密码"},
        },
    },
    "PostBody": {
        "type": "object",
        "required": ["title", "category_id"],
        "properties": {
            "title": {"type": "string", "minLength": 1, "description": "文章标题"},
            "summary": {"type": "string", "description": "摘要"},
            "content": {"type": "string", "description": "正文"},
            "category_id": {"type": "integer", "minimum": 1, "description": "分类 ID"},
        },
    },
    "CategoryBody": {
        "type": "object",
        "required": ["name"],
        "properties": {
            "name": {"type": "string", "minLength": 1, "description": "分类名"},
            "slug": {"type": "string", "description": "唯一标识，留空自动生成"},
        },
    },
    "User": {
        "type": "object",
        "properties": {
            "id": {"type": "integer"},
            "username": {"type": "string"},
            "email": {"type": "string", "format": "email"},
            "is_admin": {"type": "boolean"},
        },
    },
    "Post": {
        "type": "object",
        "properties": {
            "id": {"type": "integer"},
            "title": {"type": "string"},
            "summary": {"type": "string"},
            "content": {"type": "string"},
            "category": {"type": "object"},
            "created_at": {"type": "string", "format": "date-time"},
        },
    },
    "Category": {
        "type": "object",
        "properties": {
            "id": {"type": "integer"},
            "name": {"type": "string"},
            "slug": {"type": "string"},
        },
    },
}

# 请求体辅助
def _json_body(schema_name, required=True):
    return {
        "required": required,
        "content": {
            "application/json": {"schema": {"$ref": f"#/components/schemas/{schema_name}"}}
        },
    }


def _json_response(status, desc, schema_ref=None):
    content = None
    if schema_ref:
        content = {"application/json": {"schema": {"$ref": f"#/components/schemas/{schema_ref}"}}}
    return {str(status): {"description": desc, "content": content} if content else {"description": desc}}


PATHS = {
    "/api/auth/register": {
        "post": {
            "summary": "用户注册",
            "description": "创建用户并返回 JWT access_token；注册成功后异步发送欢迎邮件。",
            "tags": ["auth"],
            "requestBody": _json_body("RegisterBody"),
            "responses": {
                "201": {"description": "注册成功，返回 token 和用户信息"},
                "409": {"description": "用户名或邮箱已被使用"},
                "422": {"description": "请求参数校验失败（字段错误见 body.fields）"},
            },
        },
    },
    "/api/auth/login": {
        "post": {
            "summary": "用户登录",
            "description": "用户名+密码登录，成功返回 JWT access_token。",
            "tags": ["auth"],
            "requestBody": _json_body("LoginBody"),
            "responses": {
                "200": {"description": "登录成功，返回 token 和用户信息"},
                "401": {"description": "用户名或密码错误"},
                "422": {"description": "请求参数校验失败"},
            },
        },
    },
    "/api/auth/me": {
        "get": {
            "summary": "当前用户信息",
            "description": "需携带 Authorization: Bearer <token>。",
            "tags": ["auth"],
            "security": [{"bearerAuth": []}],
            "responses": {"200": _json_response(200, "当前用户信息", "User")},
        },
    },
    "/api/categories": {
        "get": {
            "summary": "分类列表",
            "description": "返回全部分类（Redis 缓存 60 秒）。",
            "tags": ["categories"],
            "responses": {"200": {"description": "分类列表"}},
        },
    },
    "/api/posts": {
        "get": {
            "summary": "文章列表",
            "description": "支持分类筛选、关键词搜索、分页（Redis 缓存 30 秒）。",
            "tags": ["posts"],
            "parameters": [
                {"name": "category", "in": "query", "schema": {"type": "string"}, "description": "分类 slug"},
                {"name": "q", "in": "query", "schema": {"type": "string"}, "description": "搜索关键词"},
                {"name": "page", "in": "query", "schema": {"type": "integer"}, "description": "页码"},
                {"name": "per_page", "in": "query", "schema": {"type": "integer"}, "description": "每页条数"},
            ],
            "responses": {"200": {"description": "文章分页列表"}},
        },
    },
    "/api/posts/{post_id}": {
        "get": {
            "summary": "文章详情",
            "description": "返回文章正文，并异步记录浏览量。",
            "tags": ["posts"],
            "parameters": [
                {"name": "post_id", "in": "path", "required": True, "schema": {"type": "integer"}}
            ],
            "responses": {
                "200": _json_response(200, "文章详情", "Post"),
                "404": {"description": "文章不存在"},
            },
        },
    },
    "/api/admin/posts": {
        "post": {
            "summary": "创建文章（管理员）",
            "description": "需要管理员权限，创建后自动失效文章列表缓存。",
            "tags": ["admin"],
            "security": [{"bearerAuth": []}],
            "requestBody": _json_body("PostBody"),
            "responses": {
                "201": {"description": "创建成功"},
                "400": {"description": "分类不存在"},
                "401": {"description": "未登录"},
                "403": {"description": "无管理员权限"},
                "422": {"description": "请求参数校验失败"},
            },
        },
    },
    "/api/admin/categories": {
        "post": {
            "summary": "创建分类（管理员）",
            "description": "需要管理员权限，创建后自动失效分类缓存。",
            "tags": ["admin"],
            "security": [{"bearerAuth": []}],
            "requestBody": _json_body("CategoryBody"),
            "responses": {
                "201": {"description": "创建成功"},
                "401": {"description": "未登录"},
                "403": {"description": "无管理员权限"},
                "409": {"description": "slug 已存在"},
                "422": {"description": "请求参数校验失败"},
            },
        },
    },
}


def build_openapi_spec():
    """构造 OpenAPI 3.0.3 规范。"""
    return {
        "openapi": "3.0.3",
        "info": {
            "title": "Flask Blog API",
            "description": "Flask 博客系统 REST API 文档（Pydantic 校验 + JWT 认证 + Redis 缓存 + Celery 异步任务）。",
            "version": "1.0.0",
        },
        "servers": [{"url": "/"}],
        "tags": [
            {"name": "auth", "description": "认证相关"},
            {"name": "posts", "description": "文章"},
            {"name": "categories", "description": "分类"},
            {"name": "admin", "description": "后台管理（需管理员）"},
        ],
        "paths": PATHS,
        "components": {
            "schemas": SCHEMAS,
            "securitySchemes": {
                "bearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
            },
        },
    }


SWAGGER_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Flask Blog API - Swagger UI</title>
  <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css"/>
</head>
<body>
<div id="swagger-ui"></div>
<script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
<script>
  window.onload = function () {
    window.ui = SwaggerUIBundle({
      url: "/openapi.json",
      dom_id: "#swagger-ui",
      deepLinking: true
    });
  };
</script>
</body>
</html>
"""


def register_openapi_routes(app):
    """在 Flask 应用上注册 /openapi.json 与 /swagger 路由。"""
    @app.get("/openapi.json")
    def openapi_json():
        return jsonify(build_openapi_spec())

    @app.get("/swagger")
    def swagger_ui():
        return SWAGGER_HTML