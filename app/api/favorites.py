from flask import Blueprint, jsonify
from sqlalchemy import func
from sqlalchemy.orm import joinedload, selectinload
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.models import Post, db, favorites, post_likes
from app import limiter

favorites_bp = Blueprint('favorites', __name__)


@favorites_bp.get('')
@jwt_required()
def list_favorites():
    """当前用户收藏的文章列表"""
    user_id = int(get_jwt_identity())
    faved_posts = Post.query.join(
        favorites, (favorites.c.post_id == Post.id)
    ).filter(
        favorites.c.user_id == user_id
    ).order_by(favorites.c.created_at.desc()).options(
        joinedload(Post.category),
        selectinload(Post.tags),
    ).all()

    # 批量计算点赞数，避免逐条 N+1
    ids = [p.id for p in faved_posts]
    like_map = {}
    if ids:
        rows = db.session.query(post_likes.c.post_id, func.count()).filter(
            post_likes.c.post_id.in_(ids)
        ).group_by(post_likes.c.post_id).all()
        like_map = {post_id: cnt for post_id, cnt in rows}

    return jsonify({'items': [p.to_dict(like_count=like_map.get(p.id, 0)) for p in faved_posts]})


@favorites_bp.post('/<int:post_id>/toggle')
@limiter.limit("30 per minute")
@jwt_required()
def toggle_favorite(post_id):
    """切换收藏状态：未收藏则收藏，已收藏则取消"""
    post = Post.query.get_or_404(post_id, description=f'文章 #{post_id} 不存在')
    user_id = int(get_jwt_identity())

    is_faved = db.session.query(favorites).filter(
        favorites.c.user_id == user_id,
        favorites.c.post_id == post.id
    ).first() is not None

    if is_faved:
        db.session.execute(
            favorites.delete().where(
                (favorites.c.user_id == user_id) &
                (favorites.c.post_id == post.id)
            )
        )
        db.session.commit()
        return jsonify({'favorited': False})
    else:
        db.session.execute(
            favorites.insert().values(user_id=user_id, post_id=post.id)
        )
        db.session.commit()
        return jsonify({'favorited': True})


@favorites_bp.get('/check/<int:post_id>')
@jwt_required()
def check_favorite(post_id):
    """检查某文章是否已被当前用户收藏"""
    user_id = int(get_jwt_identity())
    is_faved = db.session.query(favorites).filter(
        favorites.c.user_id == user_id,
        favorites.c.post_id == post_id
    ).first() is not None
    return jsonify({'favorited': is_faved})