from datetime import datetime

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from sqlalchemy import and_, func, or_, text
from sqlalchemy.orm import joinedload, selectinload

from app import limiter
from app.cache import cached
from app.models import Category, Post, Tag, db, post_likes
from app.tasks import enqueue, record_post_view

posts_bp = Blueprint('posts', __name__)


@posts_bp.get('')
@cached('posts', timeout=30)
def list_posts():
    """文章列表：支持搜索、分类筛选、分页（Redis 缓存 30 秒）。

    两种分页模式：
    - 默认（offset）：page/per_page，返回 total/pages/has_next 等页码字段，供页码导航 UI 使用；
    - 游标（keyset）：传 cursor（上一页返回的 next_cursor，格式 "unix时间戳_文章id"），
      基于 (created_at, id) 复合键定位，深分页性能恒定（O(1)），供"加载更多/无限滚动"使用。
      返回 next_cursor（下一页游标，null 表示没有更多）。
    """
    category_slug = request.args.get('category', '')
    tag_name = request.args.get('tag', '').strip()
    keyword = request.args.get('q', '').strip()
    cursor = request.args.get('cursor', '')
    per_page = min(request.args.get('per_page', 6, type=int), 50)  # 上限 50，防深分页滥用

    query = Post.query

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

    # 排序键：created_at DESC, id DESC（id 作为次级键保证稳定唯一排序）
    query = query.order_by(Post.created_at.desc(), Post.id.desc())

    # ---- keyset 游标分页：定位到游标之后，避免大 offset 全表扫描 ----
    if cursor:
        try:
            ts_str, id_str = cursor.split('_', 1)
            cursor_ts = datetime.fromisoformat(ts_str)  # 转回 datetime，与列类型一致
            cursor_id = int(id_str)
        except ValueError:
            return jsonify({'error': 'cursor 格式无效（应为 "created_at 的 ISO 字符串_id"）'}), 400
        # (created_at, id) < (cursor_ts, cursor_id)
        query = query.filter(or_(
            Post.created_at < cursor_ts,
            and_(Post.created_at == cursor_ts, Post.id < cursor_id),
        )).limit(per_page)
        items = query.options(
            joinedload(Post.category), selectinload(Post.tags)
        ).all()

        # 批量计算本页点赞数（单条聚合，避免 N+1）
        ids = [p.id for p in items]
        like_map = {}
        if ids:
            rows = db.session.query(post_likes.c.post_id, func.count()).filter(
                post_likes.c.post_id.in_(ids)
            ).group_by(post_likes.c.post_id).all()
            like_map = {post_id: cnt for post_id, cnt in rows}

        # 下一页游标 = 本页最后一条的 (created_at, id)
        next_cursor = None
        if len(items) == per_page and items:
            last = items[-1]
            next_cursor = f'{last.created_at.isoformat()}_{last.id}'

        return jsonify({
            'items': [p.to_dict(like_count=like_map.get(p.id, 0)) for p in items],
            'next_cursor': next_cursor,
            'has_more': next_cursor is not None,
        })

    # ---- 默认 offset 分页：页码导航 UI 使用 ----
    page = request.args.get('page', 1, type=int)
    pagination = query.options(
        joinedload(Post.category),
        selectinload(Post.tags),
    ).paginate(page=page, per_page=per_page, error_out=False)

    # 批量计算本页所有文章的点赞数（单条聚合查询，替代逐条 likes.count()）
    ids = [p.id for p in pagination.items]
    like_map = {}
    if ids:
        rows = db.session.query(post_likes.c.post_id, func.count()).filter(
            post_likes.c.post_id.in_(ids)
        ).group_by(post_likes.c.post_id).all()
        like_map = {post_id: cnt for post_id, cnt in rows}

    # 同时给出游标（基于本页最后一条），前端可从页码无缝切换到游标翻页
    next_cursor = None
    if pagination.items:
        last = pagination.items[-1]
        next_cursor = f'{last.created_at.isoformat()}_{last.id}'

    return jsonify({
        'items': [p.to_dict(like_count=like_map.get(p.id, 0)) for p in pagination.items],
        'total': pagination.total,
        'page': pagination.page,
        'pages': pagination.pages,
        'has_prev': pagination.has_prev,
        'has_next': pagination.has_next,
        'prev_num': pagination.prev_num,
        'next_num': pagination.next_num,
        'next_cursor': next_cursor,
        'has_more': next_cursor is not None,
    })


@posts_bp.get('/<int:post_id>')
@jwt_required(optional=True)
def get_post(post_id):
    """文章详情（异步记录浏览量，附带当前用户点赞状态）"""
    post = db.get_or_404(Post, post_id, description=f'文章 #{post_id} 不存在')
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
    post = db.get_or_404(Post, post_id, description=f'文章 #{post_id} 不存在')
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
