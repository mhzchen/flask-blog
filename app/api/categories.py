from flask import Blueprint, jsonify

from app.models import Category
from app.cache import cached

categories_bp = Blueprint('categories', __name__)


@categories_bp.get('')
@cached('categories', timeout=60)
def list_categories():
    """分类列表（Redis 缓存 60 秒，管理员改动时会失效）"""
    return jsonify({'items': [c.to_dict() for c in Category.query.all()]})