from functools import wraps
from flask import Blueprint, request, jsonify, g
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.models import User, Post, Category, db
from app.cache import invalidate
from app.schemas import PostBody, CategoryBody, validate_body

admin_bp = Blueprint('admin', __name__)


def admin_required(fn):
    """要求登录且是管理员"""
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        user = db.session.get(User, int(get_jwt_identity()))
        if user is None or not user.is_admin:
            return jsonify({'error': '需要管理员权限。'}), 403
        return fn(*args, **kwargs)
    return wrapper


# ---------- 文章管理 ----------

@admin_bp.get('/posts')
@admin_required
def list_posts():
    """后台文章列表（含正文，按时间倒序）"""
    posts = Post.query.order_by(Post.created_at.desc()).all()
    return jsonify({'items': [p.to_dict(include_content=True) for p in posts]})


@admin_bp.post('/posts')
@admin_required
@validate_body(PostBody)
def create_post():
    """创建文章（请求体经 Pydantic 校验，创建后失效文章列表缓存）"""
    body = g.validated
    category = db.session.get(Category, int(body.category_id))
    if category is None:
        return jsonify({'error': '分类不存在。'}), 400

    slug = _make_slug(body.title)
    post = Post(title=body.title, slug=slug, summary=body.summary,
                content=body.content, category_id=category.id)
    db.session.add(post)
    db.session.commit()

    invalidate('posts')
    return jsonify({'post': post.to_dict(include_content=True)}), 201


@admin_bp.put('/posts/<int:post_id>')
@admin_required
@validate_body(PostBody)
def update_post(post_id):
    """更新文章（请求体经 Pydantic 校验，更新后失效文章列表缓存）"""
    post = Post.query.get_or_404(post_id, description=f'文章 #{post_id} 不存在')
    body = g.validated
    category = db.session.get(Category, int(body.category_id))
    if category is None:
        return jsonify({'error': '分类不存在。'}), 400

    post.title = body.title
    post.summary = body.summary
    post.content = body.content
    post.category_id = category.id
    db.session.commit()

    invalidate('posts')
    return jsonify({'post': post.to_dict(include_content=True)})


@admin_bp.delete('/posts/<int:post_id>')
@admin_required
def delete_post(post_id):
    """删除文章（删除后失效文章列表缓存）"""
    post = Post.query.get_or_404(post_id, description=f'文章 #{post_id} 不存在')
    db.session.delete(post)
    db.session.commit()

    invalidate('posts')
    return jsonify({'message': '文章已删除。'})


# ---------- 分类管理 ----------

@admin_bp.post('/categories')
@admin_required
@validate_body(CategoryBody)
def create_category():
    """创建分类（请求体经 Pydantic 校验，创建后失效分类缓存）"""
    body = g.validated
    name = body.name.strip()
    slug = body.slug.strip() or _make_slug(name)
    if Category.query.filter_by(slug=slug).first():
        return jsonify({'error': 'slug 已存在。'}), 409
    cat = Category(name=name, slug=slug)
    db.session.add(cat)
    db.session.commit()

    invalidate('categories')
    return jsonify({'category': cat.to_dict()}), 201


@admin_bp.put('/categories/<int:cat_id>')
@admin_required
@validate_body(CategoryBody)
def update_category(cat_id):
    """更新分类（请求体经 Pydantic 校验，更新后失效分类缓存）"""
    cat = Category.query.get_or_404(cat_id)
    body = g.validated
    name = body.name.strip()
    slug = body.slug.strip()
    cat.name = name
    if slug:
        cat.slug = slug
    db.session.commit()

    invalidate('categories')
    return jsonify({'category': cat.to_dict()})


@admin_bp.delete('/categories/<int:cat_id>')
@admin_required
def delete_category(cat_id):
    """删除分类（删除后失效分类缓存）"""
    cat = Category.query.get_or_404(cat_id)
    db.session.delete(cat)
    db.session.commit()

    invalidate('categories')
    return jsonify({'message': '分类已删除。'})


def _make_slug(text):
    """生成一个带时间戳的唯一 slug，避免与已有标题冲突"""
    import hashlib
    base = text[:20]
    h = hashlib.md5(f'{text}{__import__("time").time()}'.encode()).hexdigest()[:6]
    return f'{base}-{h}'