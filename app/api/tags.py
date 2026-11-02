"""标签列表接口（tags_bp 挂 /api/tags）"""
from flask import Blueprint, jsonify

from app.models import Tag

tags_bp = Blueprint('tags', __name__)


@tags_bp.get('')
def list_tags():
    """标签列表（按名称排序）"""
    tags = Tag.query.order_by(Tag.name.asc()).all()
    return jsonify({'items': [t.to_dict() for t in tags]})
