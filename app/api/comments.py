"""文章评论 API：列表、发表、删除。

权限：
- 列表：公开，无需登录
- 发表：需登录
- 删除：仅评论作者本人或管理员
"""
from flask import Blueprint, g, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app import limiter
from app.idempotency import idempotent
from app.schemas import CommentBody, validate_body
from app.services import ServiceError, auth_service, comment_service

comments_bp = Blueprint("comments", __name__)


@comments_bp.get("/posts/<int:post_id>/comments")
def list_comments(post_id):
    """文章评论列表（按时间升序，分页）"""
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    try:
        pagination = comment_service.list(post_id, page, per_page)
    except ServiceError as e:
        return jsonify({"error": e.message}), e.status_code
    return jsonify({
        "items": [c.to_dict(include_replies=True) for c in pagination.items],
        "total": pagination.total,
        "page": pagination.page,
        "pages": pagination.pages,
    })


@comments_bp.post("/posts/<int:post_id>/comments")
@limiter.limit("20 per minute")
@jwt_required()
@idempotent()
@validate_body(CommentBody)
def create_comment(post_id):
    """发表评论（需登录，请求体经 Pydantic 校验）"""
    body = g.validated
    try:
        comment = comment_service.create(
            post_id, int(get_jwt_identity()),
            body.content, body.parent_id)
    except ServiceError as e:
        return jsonify({"error": e.message}), e.status_code
    comment_dict = comment.to_dict()
    # WebSocket 实时推送：新评论广播给所有在线客户端
    from app.socketio import emit_comment_new
    emit_comment_new(comment_dict)
    return jsonify({"comment": comment_dict}), 201


@comments_bp.delete("/comments/<int:comment_id>")
@jwt_required()
def delete_comment(comment_id):
    """删除评论（仅作者本人或管理员）"""
    current_user = auth_service.get_or_404(int(get_jwt_identity()))
    try:
        comment_service.delete(comment_id, current_user)
    except ServiceError as e:
        return jsonify({"error": e.message}), e.status_code
    return jsonify({"message": "评论已删除。"})
