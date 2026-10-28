from functools import wraps
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.models import User, Post, Category, db

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
def create_post():
    """创建文章"""
    data = request.get_json(silent=True) or {}
    title = (data.get('title') or '').strip()
    summary = (data.get('summary') or '').strip()
    content = data.get('content') or ''
    category_id = data.get('category_id')

    if not title:
        return jsonify({'error': '标题不能为空。'}), 400
    if not category_id:
        return jsonify({'error': '请选择分类。'}), 400
    category = db.session.get(Category, int(category_id))
    if category is None:
        return jsonify({'error': '分类不存在。'}), 400

    # 生成唯一 slug
    slug = _make_slug(title)
    post = Post(title=title, slug=slug, summary=summary, content=content,
                category_id=category.id)
    db.session.add(post)
    db.session.commit()
    return jsonify({'post': post.to_dict(include_content=True)}), 201


@admin_bp.put('/posts/<int:post_id>')
@admin_required
def update_post(post_id):
    """更新文章"""
    post = Post.query.get_or_404(post_id, description=f'文章 #{post_id} 不存在')
    data = request.get_json(silent=True) or {}
    title = (data.get('title') or '').strip()
    summary = (data.get('summary') or '').strip()
    content = data.get('content') or ''
    category_id = data.get('category_id')

    if not title:
        return jsonify({'error': '标题不能为空。'}), 400
    if not category_id:
        return jsonify({'error': '请选择分类。'}), 400
    category = db.session.get(Category, int(category_id))
    if category is None:
        return jsonify({'error': '分类不存在。'}), 400

    post.title = title
    post.summary = summary
    post.content = content
    post.category_id = category.id
    db.session.commit()
    return jsonify({'post': post.to_dict(include_content=True)})


@admin_bp.delete('/posts/<int:post_id>')
@admin_required
def delete_post(post_id):
    """删除文章"""
    post = Post.query.get_or_404(post_id, description=f'文章 #{post_id} 不存在')
    db.session.delete(post)
    db.session.commit()
    return jsonify({'message': '文章已删除。'})


# ---------- 分类管理 ----------

@admin_bp.post('/categories')
@admin_required
def create_category():
    """创建分类"""
    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()
    slug = (data.get('slug') or '').strip()
    if not name:
        return jsonify({'error': '分类名不能为空。'}), 400
    if not slug:
        slug = _make_slug(name)
    if Category.query.filter_by(slug=slug).first():
        return jsonify({'error': 'slug 已存在。'}), 409
    cat = Category(name=name, slug=slug)
    db.session.add(cat)
    db.session.commit()
    return jsonify({'category': cat.to_dict()}), 201


@admin_bp.put('/categories/<int:cat_id>')
@admin_required
def update_category(cat_id):
    """更新分类"""
    cat = Category.query.get_or_404(cat_id)
    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()
    slug = (data.get('slug') or '').strip()
    if not name:
        return jsonify({'error': '分类名不能为空。'}), 400
    cat.name = name
    if slug:
        cat.slug = slug
    db.session.commit()
    return jsonify({'category': cat.to_dict()})


@admin_bp.delete('/categories/<int:cat_id>')
@admin_required
def delete_category(cat_id):
    """删除分类"""
    cat = Category.query.get_or_404(cat_id)
    db.session.delete(cat)
    db.session.commit()
    return jsonify({'message': '分类已删除。'})


def _make_slug(text):
    """生成一个带时间戳的唯一 slug，避免与已有标题冲突"""
    import hashlib
    base = text[:20]
    h = hashlib.md5(f'{text}{__import__("time").time()}'.encode()).hexdigest()[:6]
    return f'{base}-{h}'