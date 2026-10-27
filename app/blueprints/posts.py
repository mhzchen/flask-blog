from flask import Blueprint, render_template

from app.models import Post

posts_bp = Blueprint('posts', __name__)


@posts_bp.route("/post/<int:post_id>")
def post_detail(post_id):
    """文章详情页"""
    post = Post.query.get_or_404(post_id, description=f'文章 #{post_id} 不存在')
    return render_template('post_detail.html', post=post)


@posts_bp.app_errorhandler(404)
def not_found(error):
    """自定义 404 错误页面"""
    return render_template('404.html'), 404
