"""文章接口测试：列表 / 详情 / 搜索 / 分类筛选 / 分页"""
from app import db
from app.models import Post, Category


def _add_post(app, title, slug, category, summary='摘要', content='正文'):
    p = Post(title=title, slug=slug, summary=summary, content=content,
             category_id=category.id)
    db.session.add(p)
    db.session.commit()
    return p


def test_list_posts_empty(client):
    resp = client.get('/api/posts')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['items'] == []
    assert data['total'] == 0
    assert data['page'] == 1


def test_list_posts_with_data(client, app, category):
    _add_post(app, '文章A', 'post-a', category)
    _add_post(app, '文章B', 'post-b', category)
    resp = client.get('/api/posts')
    data = resp.get_json()
    assert resp.status_code == 200
    assert data['total'] == 2
    assert len(data['items']) == 2
    # 列表不返回正文
    assert 'content' not in data['items'][0]


def test_get_post_detail(client, app, category):
    p = _add_post(app, '详情文章', 'detail-post', category, content='<h2>正文</h2>')
    resp = client.get(f'/api/posts/{p.id}')
    assert resp.status_code == 200
    data = resp.get_json()['post']
    assert data['title'] == '详情文章'
    assert data['content'] == '<h2>正文</h2>'
    assert data['category'] == category.name


def test_get_post_404(client):
    resp = client.get('/api/posts/9999')
    assert resp.status_code == 404


def test_search_by_keyword(client, app, category):
    _add_post(app, 'Flask 入门', 'flask-intro', category)
    _add_post(app, 'Vue 教程', 'vue-tutorial', category)
    resp = client.get('/api/posts', query_string={'q': 'Flask'})
    data = resp.get_json()
    assert data['total'] == 1
    assert data['items'][0]['title'] == 'Flask 入门'


def test_filter_by_category(client, app, category):
    other = Category(name='CSS', slug='css')
    db.session.add(other)
    db.session.commit()
    _add_post(app, 'py文章', 'py-1', category)
    _add_post(app, 'css文章', 'css-1', other)
    resp = client.get('/api/posts', query_string={'category': 'css'})
    data = resp.get_json()
    assert data['total'] == 1
    assert data['items'][0]['title'] == 'css文章'


def test_pagination(client, app, category):
    for i in range(3):
        _add_post(app, f'文章{i}', f'slug-{i}', category)
    resp = client.get('/api/posts', query_string={'per_page': 2, 'page': 1})
    data = resp.get_json()
    assert data['page'] == 1
    assert len(data['items']) == 2
    assert data['has_next'] is True
    assert data['pages'] == 2