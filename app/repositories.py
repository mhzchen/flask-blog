"""仓储层（Repository）：封装所有数据库访问原语。

设计原则：
- 只做"数据访问"，不含业务规则、不含 HTTP 语义、不返回 jsonify；
- 方法返回模型对象 / None / 布尔 / 计数等纯数据；
- 业务校验与组装放在 services.py，HTTP 编排放在 app/api/ 路由层。

三个层次各司其职：
    repository（本文件）→ 数据读写
    service            → 业务规则 + 跨仓储组合
    api 路由           → 解析参数、鉴权、调 service、转 JSON 响应
"""
from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import and_, func, or_, text
from sqlalchemy.orm import joinedload, selectinload

from app import db
from app.models import (
    Category,
    Comment,
    Post,
    Tag,
    User,
    favorites,
    post_likes,
)


class UserRepository:
    """用户数据访问。"""

    def get(self, user_id: int) -> Optional[User]:
        return db.session.get(User, user_id)

    def get_by_username(self, username: str) -> Optional[User]:
        return User.query.filter_by(username=username).first()

    def get_by_email(self, email: str) -> Optional[User]:
        return User.query.filter_by(email=email).first()

    def create(self, username: str, email: str, password: str) -> User:
        """创建用户并哈希密码。"""
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return user

    def get_by_github_id(self, github_id: str) -> Optional[User]:
        return User.query.filter_by(github_id=github_id).first()

    def create_github_user(self, username: str, email: str, github_id: str,
                           github_username: Optional[str] = None) -> User:
        """创建 GitHub OAuth 用户：随机不可登录密码，仅用于绑定 github_id。"""
        import secrets
        user = User(username=username, email=email,
                    github_id=github_id, github_username=github_username)
        user.set_password(secrets.token_urlsafe(32))
        db.session.add(user)
        db.session.commit()
        return user


class CategoryRepository:
    """分类数据访问。"""

    def list(self):
        return Category.query.all()

    def get(self, category_id: int) -> Optional[Category]:
        return db.session.get(Category, category_id)

    def get_by_slug(self, slug: str) -> Optional[Category]:
        return Category.query.filter_by(slug=slug).first()

    def create(self, name: str, slug: str) -> Category:
        cat = Category(name=name, slug=slug)
        db.session.add(cat)
        db.session.commit()
        return cat

    def update(self, cat: Category, name: str, slug: Optional[str] = None) -> Category:
        cat.name = name
        if slug:
            cat.slug = slug
        db.session.commit()
        return cat

    def delete(self, cat: Category) -> None:
        db.session.delete(cat)
        db.session.commit()


class TagRepository:
    """标签数据访问。"""

    def list(self):
        return Tag.query.order_by(Tag.name.asc()).all()

    def get_by_name(self, name: str) -> Optional[Tag]:
        return Tag.query.filter_by(name=name).first()

    def get_or_create(self, name: str) -> Tag:
        tag = self.get_by_name(name)
        if tag is None:
            tag = Tag(name=name)
            db.session.add(tag)
        return tag


class CommentRepository:
    """评论数据访问。"""

    def list_top_level(self, post_id: int, page: int, per_page: int):
        """文章顶级评论（分页，按时间升序，附带回复）。"""
        return (Comment.query.filter_by(post_id=post_id, parent_id=None)
                .order_by(Comment.created_at.asc())
                .paginate(page=page, per_page=per_page, error_out=False))

    def get(self, comment_id: int) -> Optional[Comment]:
        return db.session.get(Comment, comment_id)

    def create(self, post_id: int, user_id: int, content: str,
               parent_id: Optional[int] = None) -> Comment:
        comment = Comment(content=content, post_id=post_id,
                          user_id=user_id, parent_id=parent_id)
        db.session.add(comment)
        db.session.commit()
        return comment

    def delete(self, comment: Comment) -> None:
        db.session.delete(comment)
        db.session.commit()


class PostRepository:
    """文章数据访问。"""

    @staticmethod
    def _list_load():
        # 延迟构造：Post.category 是 Category.posts 的 backref，需在全部模型注册后求值
        return (joinedload(Post.category), selectinload(Post.tags))

    def get(self, post_id: int) -> Optional[Post]:
        # eager load category/tags，避免详情 to_dict 触发 N+1（懒加载 category + likes.count + tags）
        return (db.session.query(Post)
                .options(*self._list_load())
                .filter(Post.id == post_id).first())

    def get_by_id_or_404(self, post_id: int) -> Post:
        """文章不存在时返回 404（等价原路由里的 db.get_or_404）。"""
        from flask import abort
        post = self.get(post_id)
        if post is None:
            abort(404, description=f"文章 #{post_id} 不存在")
        return post

    # ---- 查询 ----
    def build_list_query(self, category_slug: str = "", tag_name: str = "",
                         keyword: str = ""):
        """构造文章列表查询（含分类/标签/全文搜索过滤 + 排序）。"""
        query = Post.query
        if category_slug:
            query = query.join(Category).filter(Category.slug == category_slug)
        if tag_name:
            query = query.join(Post.tags).filter(Tag.name == tag_name)
        if keyword:
            if db.engine.dialect.name == "mysql":
                # MySQL：走 FULLTEXT 组合索引（title+summary+content，ngram 支持中文分词）
                query = query.filter(
                    text("MATCH (title, summary, content) AGAINST (:kw)")
                    .bindparams(kw=keyword)
                )
            else:
                # SQLite（测试环境）回退 LIKE 模糊搜索
                query = query.filter(or_(
                    Post.title.ilike(f"%{keyword}%"),
                    Post.summary.ilike(f"%{keyword}%"),
                    Post.content.ilike(f"%{keyword}%")
                ))
        # 排序键：created_at DESC, id DESC（id 作为次级键保证稳定唯一排序）
        return query.order_by(Post.created_at.desc(), Post.id.desc())

    def list_cursor(self, query, cursor: str, per_page: int):
        """keyset 游标分页：返回 (items, next_cursor)。"""
        try:
            ts_str, id_str = cursor.split("_", 1)
            cursor_ts = datetime.fromisoformat(ts_str)  # 转回 datetime，与列类型一致
            cursor_id = int(id_str)
        except ValueError:
            raise ValueError('cursor 格式无效（应为 "created_at 的 ISO 字符串_id"）') from None
        # (created_at, id) < (cursor_ts, cursor_id)
        q = query.filter(or_(
            Post.created_at < cursor_ts,
            and_(Post.created_at == cursor_ts, Post.id < cursor_id),
        )).limit(per_page)
        items = q.options(*self._list_load()).all()

        next_cursor = None
        if len(items) == per_page and items:
            last = items[-1]
            next_cursor = f"{last.created_at.isoformat()}_{last.id}"
        return items, next_cursor

    def list_offset(self, query, page: int, per_page: int):
        """offset 分页：返回 (分页对象, next_cursor)。"""
        pagination = query.options(*self._list_load()).paginate(
            page=page, per_page=per_page, error_out=False)
        next_cursor = None
        if pagination.items:
            last = pagination.items[-1]
            next_cursor = f"{last.created_at.isoformat()}_{last.id}"
        return pagination, next_cursor

    def list_with_details(self, query, include_content: bool = False):
        """后台/收藏列表：返回 (posts, like_map)。"""
        posts = query.options(*self._list_load()).all()
        return posts, self.count_likes_batch([p.id for p in posts])

    # ---- 点赞 ----
    def count_likes_batch(self, post_ids) -> dict:
        """批量统计点赞数，避免逐条 N+1（单条聚合查询）。"""
        like_map: dict = {}
        if post_ids:
            rows = db.session.query(post_likes.c.post_id, func.count()).filter(
                post_likes.c.post_id.in_(post_ids)
            ).group_by(post_likes.c.post_id).all()
            like_map = {post_id: cnt for post_id, cnt in rows}
        return like_map

    def is_liked(self, user_id: int, post_id: int) -> bool:
        return db.session.query(post_likes).filter(
            post_likes.c.user_id == user_id, post_likes.c.post_id == post_id
        ).first() is not None

    def toggle_like(self, user_id: int, post: Post) -> bool:
        """切换点赞状态，返回切换后是否已赞。"""
        if self.is_liked(user_id, post.id):
            db.session.execute(
                post_likes.delete().where(
                    (post_likes.c.user_id == user_id) & (post_likes.c.post_id == post.id)
                )
            )
            db.session.commit()
            return False
        db.session.execute(post_likes.insert().values(user_id=user_id, post_id=post.id))
        db.session.commit()
        return True

    # ---- 收藏 ----
    def list_favorites(self, user_id: int):
        """当前用户收藏的文章列表（返回 (posts, like_map)）。"""
        posts = Post.query.join(
            favorites, (favorites.c.post_id == Post.id)
        ).filter(
            favorites.c.user_id == user_id
        ).order_by(favorites.c.created_at.desc()).options(
            joinedload(Post.category),
            selectinload(Post.tags),
        ).all()
        return posts, self.count_likes_batch([p.id for p in posts])

    def is_favorited(self, user_id: int, post_id: int) -> bool:
        return db.session.query(favorites).filter(
            favorites.c.user_id == user_id,
            favorites.c.post_id == post_id
        ).first() is not None

    def toggle_favorite(self, user_id: int, post_id: int) -> bool:
        """切换收藏状态，返回切换后是否已收藏。"""
        if self.is_favorited(user_id, post_id):
            db.session.execute(
                favorites.delete().where(
                    (favorites.c.user_id == user_id) & (favorites.c.post_id == post_id)
                )
            )
            db.session.commit()
            return False
        db.session.execute(
            favorites.insert().values(
                user_id=user_id, post_id=post_id,
                created_at=datetime.now(UTC))
        )
        db.session.commit()
        return True

    # ---- 写操作 ----
    def create(self, title: str, slug: str, summary: str, content: str,
               category_id: int) -> Post:
        post = Post(title=title, slug=slug, summary=summary,
                    content=content, category_id=category_id)
        db.session.add(post)
        return post

    def update(self, post: Post, title: str, summary: str, content: str,
               category_id: int) -> Post:
        post.title = title
        post.summary = summary
        post.content = content
        post.category_id = category_id
        return post

    def delete(self, post: Post) -> None:
        db.session.delete(post)


# 模块级单例：路由/服务统一从这里取仓储实例
users = UserRepository()
categories = CategoryRepository()
tags = TagRepository()
comments = CommentRepository()
posts = PostRepository()
