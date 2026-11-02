from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app import limiter
from app.cache import cached
from app.services import ServiceError, post_service
from app.tasks import enqueue, record_post_view

posts_bp = Blueprint("posts", __name__)


@posts_bp.get("")
@cached("posts", timeout=30)
def list_posts():
    """文章列表：支持搜索、分类筛选、分页（Redis 缓存 30 秒）。

    两种分页模式：
    - 默认（offset）：page/per_page，返回 total/pages/has_next 等页码字段，供页码导航 UI 使用；
    - 游标（keyset）：传 cursor（上一页返回的 next_cursor，格式 "unix时间戳_文章id"），
      基于 (created_at, id) 复合键定位，深分页性能恒定（O(1)），供"加载更多/无限滚动"使用。
      返回 next_cursor（下一页游标，null 表示没有更多）。
    """
    category_slug = request.args.get("category", "")
    tag_name = request.args.get("tag", "").strip()
    keyword = request.args.get("q", "").strip()
    cursor = request.args.get("cursor", "")
    per_page = min(request.args.get("per_page", 6, type=int), 50)  # 上限 50，防深分页滥用

    # ---- keyset 游标分页：定位到游标之后，避免大 offset 全表扫描 ----
    if cursor:
        try:
            items, like_map, next_cursor = post_service.list_cursor(
                category_slug, tag_name, keyword, cursor, per_page)
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        return jsonify({
            "items": [p.to_dict(like_count=like_map.get(p.id, 0)) for p in items],
            "next_cursor": next_cursor,
            "has_more": next_cursor is not None,
        })

    # ---- 默认 offset 分页：页码导航 UI 使用 ----
    page = request.args.get("page", 1, type=int)
    pagination, like_map, next_cursor = post_service.list_offset(
        category_slug, tag_name, keyword, page, per_page)

    # 同时给出游标（基于本页最后一条），前端可从页码无缝切换到游标翻页
    return jsonify({
        "items": [p.to_dict(like_count=like_map.get(p.id, 0)) for p in pagination.items],
        "total": pagination.total,
        "page": pagination.page,
        "pages": pagination.pages,
        "has_prev": pagination.has_prev,
        "has_next": pagination.has_next,
        "prev_num": pagination.prev_num,
        "next_num": pagination.next_num,
        "next_cursor": next_cursor,
        "has_more": next_cursor is not None,
    })


@posts_bp.get("/<int:post_id>")
@jwt_required(optional=True)
def get_post(post_id):
    """文章详情（Redis 缓存基础数据 60s，异步记录浏览量，附带当前用户点赞状态）。

    liked 是 per-user 状态，不进入缓存，每次单独查（单条索引，开销小）；
    浏览量经缓存允许延迟展示（≤60s），文章变更会 invalidate("post_detail") 失效。
    """
    try:
        data = post_service.get_detail_cached(post_id)
    except ServiceError as e:
        return jsonify({"error": e.message}), e.status_code
    enqueue(record_post_view, post_id)
    user_id = get_jwt_identity()
    data["liked"] = bool(user_id) and post_service.is_liked(int(user_id), data["id"])
    return jsonify({"post": data})


@posts_bp.post("/<int:post_id>/like")
@limiter.limit("30 per minute")
@jwt_required()
def toggle_like(post_id):
    """切换点赞：未赞则赞，已赞则取消"""
    user_id = int(get_jwt_identity())
    try:
        liked, like_count = post_service.toggle_like(user_id, post_id)
    except ServiceError as e:
        return jsonify({"error": e.message}), e.status_code
    return jsonify({"liked": liked, "like_count": like_count})
