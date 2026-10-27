from flask import Blueprint, render_template, redirect, url_for, request, flash

from flask_login import login_required, current_user
from app.models import Post, db, favorites

user_bp = Blueprint('users', __name__)


@user_bp.route("/favorite/<int:post_id>", methods=['POST'])
@login_required
def toggle_favorite(post_id):
    """切换收藏状态"""
    post = Post.query.get_or_404(post_id)

    # 检查是否已收藏：查询关联表中是否有此用户-文章组合
    is_faved = db.session.query(favorites).filter(
        favorites.c.user_id == current_user.id,
        favorites.c.post_id == post.id
    ).first() is not None

    if is_faved:
        # 取消收藏
        db.session.execute(
            favorites.delete().where(
                (favorites.c.user_id == current_user.id) &
                (favorites.c.post_id == post.id)
            )
        )
        db.session.commit()
        flash(f'已取消收藏「{post.title}」', 'info')
    else:
        # 添加收藏
        db.session.execute(
            favorites.insert().values(user_id=current_user.id, post_id=post.id)
        )
        db.session.commit()
        flash(f'已收藏「{post.title}」', 'success')

    return redirect(request.referrer or url_for('main.index'))


@user_bp.route("/favorites")
@login_required
def favorites_list():
    """当前用户的收藏列表"""
    faved_posts = Post.query.join(
        favorites, (favorites.c.post_id == Post.id)
    ).filter(
        favorites.c.user_id == current_user.id
    ).order_by(favorites.c.created_at.desc()).all()

    return render_template('favorites.html', posts=faved_posts)
