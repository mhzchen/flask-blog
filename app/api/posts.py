from flask import Blueprint, request, jsonify
from sqlalchemy import or_

from app.models import Post, Category, db

posts_bp = Blueprint('posts', __name__)


@posts_bp.get('')
def list_posts():
    """文章列表：支持搜索、分类筛选、分页"""
    category_slug = request.args.get('category', '')
    keyword = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 6, type=int)

    query = Post.query.order_by(Post.created_at.desc())

    if category_slug:
        query = query.join(Category).filter(Category.slug == category_slug)
    if keyword:
        query = query.filter(or_(
            Post.title.ilike(f'%{keyword}%'),
            Post.summary.ilike(f'%{keyword}%')
        ))

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'items': [p.to_dict() for p in pagination.items],
        'total': pagination.total,
        'page': pagination.page,
        'pages': pagination.pages,
        'has_prev': pagination.has_prev,
        'has_next': pagination.has_next,
        'prev_num': pagination.prev_num,
        'next_num': pagination.next_num,
    })


@posts_bp.get('/<int:post_id>')
def get_post(post_id):
    """文章详情"""
    post = Post.query.get_or_404(post_id, description=f'文章 #{post_id} 不存在')
    return jsonify({'post': post.to_dict(include_content=True)})