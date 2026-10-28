from datetime import datetime

from werkzeug.security import generate_password_hash, check_password_hash

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

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(200), unique=True, nullable=False)
    summary = db.Column(db.Text, default='')
    content = db.Column(db.Text, nullable=False)

    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self, include_content=False):
        """序列化为 JSON 字典。列表页可不返回正文以减小体积。"""
        data = {
            'id': self.id,
            'title': self.title,
            'slug': self.slug,
            'summary': self.summary,
            'category_id': self.category_id,
            'category': self.category.name if self.category else None,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
        }
        if include_content:
            data['content'] = self.content
        return data

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
                     db.Column('created_at', db.DateTime, default=datetime.utcnow)
                     )