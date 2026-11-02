"""服务层（Service）：业务规则 + 跨仓储组合。

设计原则：
- 只做"业务逻辑"，不直接操作 db.session（统一走 repositories）；
- 不解析 HTTP 参数、不返回 jsonify（那是路由层的事）；
- 业务校验失败抛 ServiceError(message, status_code)，由路由层转 JSON 响应。

分层约定：
    repository → 数据读写
    service    → 业务规则（本文件）
    api 路由   → HTTP 编排
"""
from typing import Optional

from app.cache import invalidate
from app.models import Comment, Post, User
from app.repositories import (
    categories as category_repo,
)
from app.repositories import (
    comments as comment_repo,
)
from app.repositories import (
    posts as post_repo,
)
from app.repositories import (
    tags as tag_repo,
)
from app.repositories import (
    users as user_repo,
)
from app.sanitize import sanitize_html


class ServiceError(Exception):
    """业务校验失败：携带对外的 HTTP 状态码与错误消息。"""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


# ============================ 认证 / 用户 ============================

class AuthService:
    """注册 / 登录 / 用户信息。"""

    def register(self, username: str, email: str, password: str) -> User:
        """注册：校验唯一性后创建用户。已占用抛 409。"""
        if user_repo.get_by_username(username):
            raise ServiceError("用户名已被使用。", 409)
        if user_repo.get_by_email(email):
            raise ServiceError("邮箱已被注册。", 409)
        return user_repo.create(username, email, password)

    def login(self, username: str, password: str) -> Optional[User]:
        """登录：校验用户名 + 密码，失败返回 None（由路由转 401）。"""
        user = user_repo.get_by_username(username)
        if user is None or not user.check_password(password):
            return None
        return user

    def get_or_404(self, user_id: int) -> User:
        """取当前用户，不存在抛 404。"""
        user = user_repo.get(user_id)
        if user is None:
            raise ServiceError("用户不存在。", 404)
        return user

    current_user = get_or_404


# ============================ 文章 ============================

class PostService:
    """文章列表 / 详情 / 点赞。"""

    def list_offset(self, category_slug: str, tag_name: str, keyword: str,
                    page: int, per_page: int):
        """offset 分页列表：返回 (items, like_map, pagination, next_cursor)。"""
        query = post_repo.build_list_query(category_slug, tag_name, keyword)
        pagination, next_cursor = post_repo.list_offset(query, page, per_page)
        like_map = post_repo.count_likes_batch([p.id for p in pagination.items])
        return pagination, like_map, next_cursor

    def list_cursor(self, category_slug: str, tag_name: str, keyword: str,
                    cursor: str, per_page: int):
        """keyset 游标分页列表：返回 (items, like_map, next_cursor)。"""
        query = post_repo.build_list_query(category_slug, tag_name, keyword)
        items, next_cursor = post_repo.list_cursor(query, cursor, per_page)
        like_map = post_repo.count_likes_batch([p.id for p in items])
        return items, like_map, next_cursor

    def get_detail(self, post_id: int) -> Post:
        return post_repo.get_by_id_or_404(post_id)

    def is_liked(self, user_id: int, post_id: int) -> bool:
        return post_repo.is_liked(user_id, post_id)

    def toggle_like(self, user_id: int, post_id: int):
        """切换点赞，返回 (切换后是否已赞, 最新点赞数)。"""
        post = post_repo.get_by_id_or_404(post_id)
        liked = post_repo.toggle_like(user_id, post)
        return liked, post.likes.count()


# ============================ 评论 ============================

class CommentService:
    """评论列表 / 发表 / 删除。"""

    def list(self, post_id: int, page: int, per_page: int):
        """文章顶级评论分页列表。文章不存在抛 404。"""
        post_repo.get_by_id_or_404(post_id)
        return comment_repo.list_top_level(post_id, page, per_page)

    def create(self, post_id: int, user_id: int, content: str,
               parent_id: Optional[int] = None) -> Comment:
        """发表评论：校验父评论归属，扁平化回复到顶级。"""
        post_repo.get_by_id_or_404(post_id)
        content = content.strip()
        if not content:
            raise ServiceError("评论内容不能为空。", 422)
        if parent_id:
            parent = comment_repo.get(parent_id)
            if parent is None or parent.post_id != post_id:
                raise ServiceError("要回复的评论不存在或不属于该文章。", 400)
            parent_id = parent.parent_id or parent.id  # 扁平化：回复永远挂在顶级评论下
        return comment_repo.create(post_id, user_id, content, parent_id)

    def delete(self, comment_id: int, current_user: User) -> None:
        """删除评论：仅作者本人或管理员。无权限抛 403。"""
        comment = comment_repo.get(comment_id)
        if comment is None:
            raise ServiceError("评论不存在。", 404)
        if current_user.id != comment.user_id and not current_user.is_admin:
            raise ServiceError("没有权限删除该评论。", 403)
        comment_repo.delete(comment)


# ============================ 收藏 ============================

class FavoriteService:
    """收藏列表 / 切换 / 检查。"""

    def list(self, user_id: int):
        """当前用户收藏的文章列表：返回 (posts, like_map)。"""
        return post_repo.list_favorites(user_id)

    def toggle(self, user_id: int, post_id: int) -> bool:
        """切换收藏，返回切换后是否已收藏。"""
        post_repo.get_by_id_or_404(post_id)
        return post_repo.toggle_favorite(user_id, post_id)

    def check(self, user_id: int, post_id: int) -> bool:
        return post_repo.is_favorited(user_id, post_id)


# ============================ 分类 ============================

class CategoryService:
    """分类列表 / 管理。"""

    def list(self):
        return category_repo.list()

    def get_or_404(self, category_id: int):
        cat = category_repo.get(category_id)
        if cat is None:
            raise ServiceError("分类不存在。", 404)
        return cat

    def create(self, name: str, slug: str):
        """创建分类：slug 冲突抛 409。"""
        name = name.strip()
        slug = slug.strip() or _make_slug(name)
        if category_repo.get_by_slug(slug):
            raise ServiceError("slug 已存在。", 409)
        cat = category_repo.create(name, slug)
        invalidate("categories")
        return cat

    def update(self, category_id: int, name: str, slug: str):
        cat = self.get_or_404(category_id)
        category_repo.update(cat, name.strip(), slug.strip() or None)
        invalidate("categories")
        return cat

    def delete(self, category_id: int) -> None:
        cat = self.get_or_404(category_id)
        category_repo.delete(cat)
        invalidate("categories")


# ============================ 后台管理（文章） ============================

class AdminPostService:
    """后台文章管理：列表 / 创建 / 更新 / 删除。"""

    def require_admin(self, user_id: int) -> None:
        """校验用户是管理员，否则抛 403。"""
        user = user_repo.get(user_id)
        if user is None or not user.is_admin:
            raise ServiceError("需要管理员权限。", 403)

    def list(self):
        """后台文章列表（含正文，按时间倒序）：返回 (posts, like_map)。"""
        query = Post.query.order_by(Post.created_at.desc())
        return post_repo.list_with_details(query, include_content=True)

    def create(self, title: str, summary: str, content: str,
               category_id: int, tags):
        category = category_repo.get(category_id)
        if category is None:
            raise ServiceError("分类不存在。", 400)
        slug = _make_slug(title)
        # XSS 防护：内容净化后再入库，剔除脚本/事件属性等危险 HTML
        post = post_repo.create(title, slug, summary, sanitize_html(content),
                                category.id)
        _sync_tags(post, tags)
        db_commit()
        invalidate("posts")
        return post

    def update(self, post_id: int, title: str, summary: str, content: str,
               category_id: int, tags):
        post = post_repo.get_by_id_or_404(post_id)
        category = category_repo.get(category_id)
        if category is None:
            raise ServiceError("分类不存在。", 400)
        post_repo.update(post, title, summary, sanitize_html(content), category.id)
        _sync_tags(post, tags)
        db_commit()
        invalidate("posts")
        return post

    def delete(self, post_id: int) -> None:
        post = post_repo.get_by_id_or_404(post_id)
        post_repo.delete(post)
        db_commit()
        invalidate("posts")


# ============================ 工具函数 ============================

def db_commit():
    """统一提交当前会话（业务层只调用它，不直接碰 db.session）。"""
    from app import db
    db.session.commit()


def _make_slug(text: str) -> str:
    """生成一个带时间戳的唯一 slug，避免与已有标题冲突。"""
    import hashlib
    import time
    base = text[:20]
    h = hashlib.md5(f"{text}{time.time()}".encode()).hexdigest()[:6]
    return f"{base}-{h}"


def _sync_tags(post, tag_names) -> None:
    """把标签名列表同步到文章的标签集合（按需创建 Tag，去重、去空白）。"""
    post.tags = []
    for name in dict.fromkeys(t.strip() for t in (tag_names or []) if t.strip()):
        tag = tag_repo.get_or_create(name)
        post.tags.append(tag)


# 模块级单例
auth_service = AuthService()
post_service = PostService()
comment_service = CommentService()
favorite_service = FavoriteService()
category_service = CategoryService()
admin_post_service = AdminPostService()
