from flask import Blueprint, request, jsonify
from sqlalchemy import or_, text
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.models import Post, Category, Tag, db, post_likes
from app import limiter
from app.cache import cached
from app.tasks import enqueue, record_post_view

posts_bp = Blueprint('posts', __name__)


@posts_bp.get('')
@cached('posts', timeout=30)
def list_posts():
    """文章列表：支持搜索、分类筛选、分页（Redis 缓存 30 秒）"""
    category_slug = request.args.get('category', '')
    tag_name = request.args.get('tag', '').strip()
    keyword = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 6, type=int)

    query = Post.query.order_by(Post.created_at.desc())

    if category_slug:
        query = query.join(Category).filter(Category.slug == category_slug)
    if tag_name:
        query = query.join(Post.tags).filter(Tag.name == tag_name)
    if keyword:
        if db.engine.dialect.name == 'mysql':
            # MySQL：走 FULLTEXT 组合索引（title+summary+content，ngram 支持中文分词）
            query = query.filter(
                text("MATCH (title, summary, content) AGAINST (:kw)").bindparams(kw=keyword)
            )
        else:
            # SQLite（测试环境）回退 LIKE 模糊搜索
            query = query.filter(or_(
                Post.title.ilike(f'%{keyword}%'),
                Post.summary.ilike(f'%{keyword}%'),
                Post.content.ilike(f'%{keyword}%')
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
@jwt_required(optional=True)
def get_post(post_id):
    """文章详情（异步记录浏览量，附带当前用户点赞状态）"""
    post = Post.query.get_or_404(post_id, description=f'文章 #{post_id} 不存在')
    enqueue(record_post_view, post_id)
    data = post.to_dict(include_content=True)
    user_id = get_jwt_identity()
    data['liked'] = bool(user_id) and db.session.query(post_likes).filter(
        post_likes.c.user_id == int(user_id), post_likes.c.post_id == post.id
    ).first() is not None
    return jsonify({'post': data})

@posts_bp.post('/<int:post_id>/like')
@limiter.limit("30 per minute")
@jwt_required()
def toggle_like(post_id):
    """切换点赞：未赞则赞，已赞则取消"""
    post = Post.query.get_or_404(post_id, description=f'文章 #{post_id} 不存在')
    user_id = int(get_jwt_identity())
    is_liked = db.session.query(post_likes).filter(
        post_likes.c.user_id == user_id, post_likes.c.post_id == post.id
    ).first() is not None
    if is_liked:
        db.session.execute(
            post_likes.delete().where(
                (post_likes.c.user_id == user_id) & (post_likes.c.post_id == post.id)
            )
        )
        db.session.commit()
        liked = False
    else:
        db.session.execute(post_likes.insert().values(user_id=user_id, post_id=post.id))
        db.session.commit()
        liked = True
    return jsonify({'liked': liked, 'like_count': post.likes.count()})
