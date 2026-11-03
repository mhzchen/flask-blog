from datetime import UTC, datetime

from werkzeug.security import check_password_hash, generate_password_hash

from app import db


class Category(db.Model):
    """文章分类"""
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    slug = db.Column(db.String(50), unique=True, nullable=False)

    posts = db.relationship('Post', backref='category', lazy='dynamic')

    def to_dict(self):
        return {'id': self.id, 'name': self.name, 'slug': self.slug}

    def __repr__(self):
        return f'<Category {self.name}>'


class Post(db.Model):
    """博客文章"""
    __tablename__ = 'posts'
    __table_args__ = ()

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(200), nullable=False, index=False)
    slug = db.Column(db.String(200), unique=True, nullable=False)
    summary = db.Column(db.Text, default='')
    content = db.Column(db.Text, nullable=False)

    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), index=True)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
    views = db.Column(db.Integer, nullable=False, default=0)

    def to_dict(self, include_content=False, like_count=None):
        """序列化为 JSON 字典。列表页可不返回正文以减小体积。

        默认惰性读取 tags/category（适合详情页单条场景）；
        列表页由调用方预加载关系并传入 like_count，避免 N+1 查询。
        """
        data = {
            'id': self.id,
            'title': self.title,
            'slug': self.slug,
            'summary': self.summary,
            'category_id': self.category_id,
            'category': self.category.name if self.category else None,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'views': self.views,
            'like_count': self.likes.count() if like_count is None else like_count,
            'tags': [t.name for t in self.tags],
        }
        if include_content:
            data['content'] = self.content
        return data

    tags = db.relationship('Tag', secondary='post_tags', backref='posts', lazy='select')
    likes = db.relationship('User', secondary='post_likes', backref='liked_posts', lazy='dynamic')

    def __repr__(self):
        return f'<Post {self.title}>'


class User(db.Model):
    """用户模型"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)

    def set_password(self, password):
        """对密码进行哈希加密（永远不存明文密码）"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """验证密码是否匹配"""
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {'id': self.id, 'username': self.username, 'email': self.email, 'is_admin': self.is_admin}

    def __repr__(self):
        return f'<User {self.username}>'


# 收藏关联表：多对多（一个用户收藏多篇文章，一篇文章被多个用户收藏）
favorites = db.Table('favorites',
                     db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
                     db.Column('post_id', db.Integer, db.ForeignKey('posts.id'), primary_key=True),
                     db.Column('created_at', db.DateTime, default=lambda: datetime.now(UTC))
                     )

class Comment(db.Model):
    """文章评论"""
    __tablename__ = 'comments'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('comments.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))

    # 关系：to_dict 里能拿到评论者用户名
    user = db.relationship('User', backref='comments')
    post = db.relationship('Post', backref='comments')
    parent = db.relationship('Comment', remote_side=[id], backref='replies')

    def to_dict(self, include_replies=False):
        data = {
            'id': self.id,
            'content': self.content,
            'user_id': self.user_id,
            'username': self.user.username if self.user else None,
            'post_id': self.post_id,
            'parent_id': self.parent_id,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
        }
        if include_replies:
            data['replies'] = [
                r.to_dict() for r in sorted(self.replies, key=lambda x: x.created_at)
            ]
        return data

    def __repr__(self):
        return f'<Comment {self.id} on post {self.post_id}>'


# 文章标签关联表：多对多（一篇文章多个标签，一个标签多篇文章）
post_tags = db.Table('post_tags',
                     db.Column('post_id', db.Integer, db.ForeignKey('posts.id'), primary_key=True),
                     db.Column('tag_id', db.Integer, db.ForeignKey('tags.id'), primary_key=True)
                     )

# 点赞关联表：多对多（用户点赞文章）
post_likes = db.Table('post_likes',
                     db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
                     db.Column('post_id', db.Integer, db.ForeignKey('posts.id'), primary_key=True),
                     db.Column('created_at', db.DateTime, default=lambda: datetime.now(UTC))
                     )


class Tag(db.Model):
    # 文章标签
    __tablename__ = 'tags'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

    def to_dict(self):
        return {'id': self.id, 'name': self.name}

    def __repr__(self):
        return f'<Tag {self.name}>'
