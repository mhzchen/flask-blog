"""分类接口测试"""
from app import db
from app.models import Category


def test_list_categories_empty(client):
    resp = client.get('/api/categories')
    assert resp.status_code == 200
    assert resp.get_json()['items'] == []


def test_list_categories_with_data(client):
    db.session.add(Category(name='Python', slug='python'))
    db.session.add(Category(name='Flask', slug='flask'))
    db.session.commit()
    resp = client.get('/api/categories')
    data = resp.get_json()
    assert resp.status_code == 200
    slugs = [c['slug'] for c in data['items']]
    assert 'python' in slugs and 'flask' in slugs