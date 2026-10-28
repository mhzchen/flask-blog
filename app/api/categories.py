from flask import Blueprint, jsonify

from app.models import Category

categories_bp = Blueprint('categories', __name__)


@categories_bp.get('')
def list_categories():
    """分类列表"""
    return jsonify({'items': [c.to_dict() for c in Category.query.all()]})