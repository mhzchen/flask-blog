"""标签系统 + 搜索优化测试。

覆盖：创建/更新文章带标签、标签去重去空白、标签列表、按标签筛选、
文章详情返回标签、标题/正文关键词搜索。
"""


def test_create_post_with_tags(client, app, category, admin_headers):
    resp = client.post('/api/v1/admin/posts', headers=admin_headers, json={
        'title': '带标签的文章', 'summary': 's', 'content': '<p>c</p>',
        'category_id': category.id, 'tags': ['Flask', 'Web'],
    })
    assert resp.status_code == 201
    assert resp.get_json()['post']['tags'] == ['Flask', 'Web']


def test_create_post_tags_dedup_and_trim(client, app, category, admin_headers):
    resp = client.post('/api/v1/admin/posts', headers=admin_headers, json={
        'title': '去重', 'summary': 's', 'content': 'c',
        'category_id': category.id, 'tags': ['Flask', ' Flask ', 'Flask', '', 'Web'],
    })
    assert resp.status_code == 201
    assert resp.get_json()['post']['tags'] == ['Flask', 'Web']


def test_update_post_tags(client, app, category, post, admin_headers):
    resp = client.put(f'/api/v1/admin/posts/{post.id}', headers=admin_headers, json={
        'title': post.title, 'summary': post.summary, 'content': post.content,
        'category_id': category.id, 'tags': ['更新标签'],
    })
    assert resp.status_code == 200
    assert resp.get_json()['post']['tags'] == ['更新标签']


def test_list_tags(client, app, category, admin_headers):
    client.post('/api/v1/admin/posts', headers=admin_headers, json={
        'title': '标签文', 'summary': '', 'content': 'c',
        'category_id': category.id, 'tags': ['Flask', 'Web'],
    })
    resp = client.get('/api/v1/tags')
    assert resp.status_code == 200
    names = [t['name'] for t in resp.get_json()['items']]
    assert 'Flask' in names and 'Web' in names


def test_filter_posts_by_tag(client, app, category, post, admin_headers):
    # post fixture 无标签；新建一个带 Flask 标签的文章
    client.post('/api/v1/admin/posts', headers=admin_headers, json={
        'title': 'Flask 进阶', 'summary': '', 'content': 'c',
        'category_id': category.id, 'tags': ['Flask'],
    })
    resp = client.get('/api/v1/posts', query_string={'tag': 'Flask'})
    assert resp.status_code == 200
    titles = [p['title'] for p in resp.get_json()['items']]
    assert 'Flask 进阶' in titles
    assert 'Hello Flask' not in titles  # post 无 Flask 标签


def test_post_detail_includes_tags(client, app, category, post, admin_headers):
    client.put(f'/api/v1/admin/posts/{post.id}', headers=admin_headers, json={
        'title': post.title, 'summary': post.summary, 'content': post.content,
        'category_id': category.id, 'tags': ['Flask'],
    })
    resp = client.get(f'/api/v1/posts/{post.id}')
    assert resp.status_code == 200
    assert resp.get_json()['post']['tags'] == ['Flask']


# ---------- 搜索优化 ----------


def test_search_title(client, app, category, post):
    resp = client.get('/api/v1/posts', query_string={'q': 'Flask'})
    assert resp.status_code == 200
    assert any(p['title'] == 'Hello Flask' for p in resp.get_json()['items'])


def test_search_content(client, app, category, post):
    resp = client.get('/api/v1/posts', query_string={'q': '测试正文'})
    assert resp.status_code == 200
    assert any(p['title'] == 'Hello Flask' for p in resp.get_json()['items'])


def test_search_no_match(client, app, category, post):
    resp = client.get('/api/v1/posts', query_string={'q': '不存在关键词xyz'})
    assert resp.status_code == 200
    assert resp.get_json()['items'] == []
