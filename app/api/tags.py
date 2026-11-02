"""标签列表接口（tags_bp 挂 /api/tags）"""
from flask import Blueprint, jsonify

from app.repositories import tags as tag_repo

tags_bp = Blueprint("tags", __name__)


@tags_bp.get("")
def list_tags():
    """标签列表（按名称排序）"""
    return jsonify({"items": [t.to_dict() for t in tag_repo.list()]})
