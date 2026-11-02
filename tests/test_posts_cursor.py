"""分页游标(keyset)测试：验证 offset 兼容、游标翻页无重复无遗漏、坏 cursor 拒绝"""


def _make_posts(client, admin_headers, category, n):
    """创建 n 篇文章，返回它们的 id 列表（按 created_at 升序）。"""
    ids = []
    for i in range(n):
        resp = client.post('/api/admin/posts', json={
            'title': f'游标测试文章{i}', 'slug': f'cursor-{i}',
            'content': f'<p>正文{i}</p>',
            'category_id': category.id, 'tags': [],
        }, headers=admin_headers)
        assert resp.status_code == 201
        ids.append(resp.get_json()['post']['id'])
    return ids


class TestCursorPagination:
    def test_offset_mode_still_works(self, client, category):
        """默认 offset 分页字段保持兼容（页码导航 UI 依赖）"""
        resp = client.get('/api/posts?page=1&per_page=2')
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'total' in data and 'page' in data and 'pages' in data and 'has_next' in data

    def test_cursor_no_dup_no_missing(self, client, admin_headers, category):
        """游标翻页遍历所有文章，无重复、无遗漏"""
        n = 7
        _make_posts(client, admin_headers, category, n)
        per_page = 3
        seen = []
        cursor = ''
        pages = 0
        while True:
            url = f'/api/posts?per_page={per_page}'
            if cursor:
                url += f'&cursor={cursor}'
            data = client.get(url).get_json()
            items = data['items']
            assert len(items) <= per_page
            for it in items:
                assert it['id'] not in seen, '出现重复文章'
                seen.append(it['id'])
            pages += 1
            if data['next_cursor'] is None:
                break
            cursor = data['next_cursor']
            assert pages < 100  # 防死循环
        assert pages == 3  # 7 篇 / 3 每页 = 3 页
        assert len(seen) == n
        assert len(set(seen)) == n

    def test_cursor_invalid_returns_400(self, client):
        resp = client.get('/api/posts?cursor=bad_cursor')
        assert resp.status_code == 400

    def test_cursor_exhausts_has_more_false(self, client, admin_headers, category):
        """满页时返回 next_cursor；用该游标再请求得到空列表（has_more=false），表示已取完"""
        _make_posts(client, admin_headers, category, 2)
        data = client.get('/api/posts?per_page=2').get_json()
        # keyset 语义：满页即可能还有更多，需再请求一次确认
        assert data['next_cursor'] is not None
        assert data['has_more'] is True
        # 用游标再请求 -> 空列表，结束
        nxt = data['next_cursor']
        data2 = client.get(f'/api/posts?per_page=2&cursor={nxt}').get_json()
        assert data2['items'] == []
        assert data2['next_cursor'] is None
        assert data2['has_more'] is False
