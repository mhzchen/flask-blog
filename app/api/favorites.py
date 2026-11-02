from flask import Blueprint, jsonify
from flask_jwt_extended import get_jwt_identity, jwt_required

from app import limiter
from app.services import ServiceError, favorite_service

favorites_bp = Blueprint("favorites", __name__)


@favorites_bp.get("")
@jwt_required()
def list_favorites():
    """当前用户收藏的文章列表"""
    user_id = int(get_jwt_identity())
    posts, like_map = favorite_service.list(user_id)
    return jsonify({"items": [p.to_dict(like_count=like_map.get(p.id, 0)) for p in posts]})


@favorites_bp.post("/<int:post_id>/toggle")
@limiter.limit("30 per minute")
@jwt_required()
def toggle_favorite(post_id):
    """切换收藏状态：未收藏则收藏，已收藏则取消"""
    user_id = int(get_jwt_identity())
    try:
        favorited = favorite_service.toggle(user_id, post_id)
    except ServiceError as e:
        return jsonify({"error": e.message}), e.status_code
    return jsonify({"favorited": favorited})


@favorites_bp.get("/check/<int:post_id>")
@jwt_required()
def check_favorite(post_id):
    """检查某文章是否已被当前用户收藏"""
    user_id = int(get_jwt_identity())
    return jsonify({"favorited": favorite_service.check(user_id, post_id)})
