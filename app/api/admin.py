from functools import wraps

from flask import Blueprint, g, jsonify
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.schemas import CategoryBody, PostBody, validate_body
from app.services import (
    ServiceError,
    admin_post_service,
    category_service,
)

admin_bp = Blueprint("admin", __name__)


def admin_required(fn):
    """要求登录且是管理员"""
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        try:
            admin_post_service.require_admin(int(get_jwt_identity()))
        except ServiceError as e:
            return jsonify({"error": e.message}), e.status_code
        return fn(*args, **kwargs)
    return wrapper


# ---------- 文章管理 ----------

@admin_bp.get("/posts")
@admin_required
def list_posts():
    """后台文章列表（含正文，按时间倒序）"""
    posts, like_map = admin_post_service.list()
    return jsonify({
        "items": [p.to_dict(include_content=True, like_count=like_map.get(p.id, 0))
                  for p in posts]
    })


@admin_bp.post("/posts")
@admin_required
@validate_body(PostBody)
def create_post():
    """创建文章（请求体经 Pydantic 校验，创建后失效文章列表缓存）"""
    body = g.validated
    try:
        post = admin_post_service.create(
            body.title, body.summary, body.content,
            int(body.category_id), body.tags)
    except ServiceError as e:
        return jsonify({"error": e.message}), e.status_code
    _enqueue_search(post.id, unindex=False)
    return jsonify({"post": post.to_dict(include_content=True)}), 201


@admin_bp.put("/posts/<int:post_id>")
@admin_required
@validate_body(PostBody)
def update_post(post_id):
    """更新文章（请求体经 Pydantic 校验，更新后失效文章列表缓存）"""
    body = g.validated
    try:
        post = admin_post_service.update(
            post_id, body.title, body.summary, body.content,
            int(body.category_id), body.tags)
    except ServiceError as e:
        return jsonify({"error": e.message}), e.status_code
    _enqueue_search(post_id, unindex=False)
    return jsonify({"post": post.to_dict(include_content=True)})


@admin_bp.delete("/posts/<int:post_id>")
@admin_required
def delete_post(post_id):
    """删除文章（删除后失效文章列表缓存）"""
    try:
        admin_post_service.delete(post_id)
    except ServiceError as e:
        return jsonify({"error": e.message}), e.status_code
    _enqueue_search(post_id, unindex=True)
    return jsonify({"message": "文章已删除。"})


# ---------- 分类管理 ----------

@admin_bp.post("/categories")
@admin_required
@validate_body(CategoryBody)
def create_category():
    """创建分类（请求体经 Pydantic 校验，创建后失效分类缓存）"""
    body = g.validated
    try:
        cat = category_service.create(body.name, body.slug)
    except ServiceError as e:
        return jsonify({"error": e.message}), e.status_code
    return jsonify({"category": cat.to_dict()}), 201


@admin_bp.put("/categories/<int:cat_id>")
@admin_required
@validate_body(CategoryBody)
def update_category(cat_id):
    """更新分类（请求体经 Pydantic 校验，更新后失效分类缓存）"""
    body = g.validated
    try:
        cat = category_service.update(cat_id, body.name, body.slug)
    except ServiceError as e:
        return jsonify({"error": e.message}), e.status_code
    return jsonify({"category": cat.to_dict()})


@admin_bp.delete("/categories/<int:cat_id>")
@admin_required
def delete_category(cat_id):
    """删除分类（删除后失效分类缓存）"""
    try:
        category_service.delete(cat_id)
    except ServiceError as e:
        return jsonify({"error": e.message}), e.status_code
    return jsonify({"message": "分类已删除。"})


def _enqueue_search(post_id, unindex: bool):
    """文章增删改后异步同步 Meilisearch 索引（#56）。

    投递失败/Meilisearch 不可用都由 enqueue 兜底（降级同步或记日志），绝不拖垮请求。
    """
    try:
        from app.tasks import enqueue, index_post_search, unindex_post_search
        if unindex:
            enqueue(unindex_post_search, post_id)
        else:
            enqueue(index_post_search, post_id)
    except Exception:
        pass
