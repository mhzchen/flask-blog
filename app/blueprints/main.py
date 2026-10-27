from flask import Blueprint, render_template, request

from sqlalchemy import or_
from app.models import Post, Category

main_bp = Blueprint('main', __name__)


@main_bp.route("/")
def index():
    """博客首页：搜索 + 分类筛选 + 分页"""
    category_slug = request.args.get('category', '')
    keyword = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 6

    # 基础查询
    posts_query = Post.query.order_by(Post.created_at.desc())

    # 分类筛选
    if category_slug:
        posts_query = posts_query.join(Category).filter(Category.slug == category_slug)

    # 关键词搜索（标题或摘要）
    if keyword:
        posts_query = posts_query.filter(
            or_(
                Post.title.ilike(f'%{keyword}%'),
                Post.summary.ilike(f'%{keyword}%')
            )
        )

    # 分页（error_out=False：页码超出范围时不报 404）
    pagination = posts_query.paginate(page=page, per_page=per_page, error_out=False)
    posts = pagination.items

    return render_template('index.html',
                           posts=posts, pagination=pagination,
                           categories=Category.query.all(),
                           category_slug=category_slug, keyword=keyword)


@main_bp.route("/about")
def about():
    """关于页面"""
    return '<h1>关于本站</h1><p>记录前端与后端的学习笔记。</p>'
