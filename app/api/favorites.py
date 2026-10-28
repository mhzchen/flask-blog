from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.models import Post, db, favorites

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
    ).order_by(favorites.c.created_at.desc()).all()

    return jsonify({'items': [p.to_dict() for p in faved_posts]})


@favorites_bp.post('/<int:post_id>/toggle')
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