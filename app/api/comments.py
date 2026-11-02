"""文章评论 API：列表、发表、删除。

权限：
- 列表：公开，无需登录
- 发表：需登录
- 删除：仅评论作者本人或管理员
"""
from flask import Blueprint, g, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app import limiter
from app.models import Comment, Post, User, db
from app.schemas import CommentBody, validate_body

comments_bp = Blueprint('comments', __name__)


@comments_bp.get('/posts/<int:post_id>/comments')
def list_comments(post_id):
    """文章评论列表（按时间升序，分页）"""
    db.get_or_404(Post, post_id, description=f'文章 #{post_id} 不存在')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    pagination = (Comment.query.filter_by(post_id=post_id, parent_id=None)
                  .order_by(Comment.created_at.asc())
                  .paginate(page=page, per_page=per_page, error_out=False))

    return jsonify({
        'items': [c.to_dict(include_replies=True) for c in pagination.items],
        'total': pagination.total,
        'page': pagination.page,
        'pages': pagination.pages,
    })


@comments_bp.post('/posts/<int:post_id>/comments')
@limiter.limit("20 per minute")
@jwt_required()
@validate_body(CommentBody)
def create_comment(post_id):
    """发表评论（需登录，请求体经 Pydantic 校验）"""
    db.get_or_404(Post, post_id, description=f'文章 #{post_id} 不存在')
    body = g.validated
    content = body.content.strip()
    if not content:
        return jsonify({'error': '评论内容不能为空。'}), 422
    parent_id = body.parent_id
    if parent_id:
        parent = db.session.get(Comment, parent_id)
        if parent is None or parent.post_id != post_id:
            return jsonify({'error': '要回复的评论不存在或不属于该文章。'}), 400
        parent_id = parent.parent_id or parent.id
    comment = Comment(content=content, post_id=post_id,
                      user_id=int(get_jwt_identity()), parent_id=parent_id)
    db.session.add(comment)
    db.session.commit()
    return jsonify({'comment': comment.to_dict()}), 201


@comments_bp.delete('/comments/<int:comment_id>')
@jwt_required()
def delete_comment(comment_id):
    """删除评论（仅作者本人或管理员）"""
    comment = db.get_or_404(Comment, comment_id, description=f'评论 #{comment_id} 不存在')
    current_user = db.session.get(User, int(get_jwt_identity()))
    if current_user is None or (current_user.id != comment.user_id and not current_user.is_admin):
        return jsonify({'error': '没有权限删除该评论。'}), 403
    db.session.delete(comment)
    db.session.commit()
    return jsonify({'message': '评论已删除。'})
