"""XSS 防护测试：HTML 净化工具 + 文章创建时净化入库"""
from app.sanitize import sanitize_html


class TestSanitizeHtml:
    def test_removes_script_tags(self):
        assert '<script>' not in sanitize_html('<p>hi</p><script>alert(1)</script>')

    def test_removes_event_attributes(self):
        out = sanitize_html('<img src="x" onerror="alert(1)">')
        assert 'onerror' not in out

    def test_removes_javascript_protocol(self):
        out = sanitize_html('<a href="javascript:alert(1)">link</a>')
        assert 'javascript:' not in out
        assert 'link' in out

    def test_keeps_safe_html(self):
        out = sanitize_html('<p><strong>bold</strong> and <a href="https://x.com">link</a></p>')
        assert '<strong>bold</strong>' in out
        assert 'href="https://x.com"' in out

    def test_empty_and_none(self):
        assert sanitize_html('') == ''
        assert sanitize_html(None) == ''

    def test_removes_iframe(self):
        out = sanitize_html('<p>ok</p><iframe src="x"></iframe>')
        assert '<iframe' not in out


def test_create_post_sanitizes_content(client, admin_headers, category):
    """通过 admin API 创建含脚本的文章，验证入库内容已被净化"""
    payload = {
        'title': 'XSS测试', 'slug': 'xss-test',
        'content': '<p>正文</p><script>alert(1)</script>',
        'category_id': category.id, 'tags': [],
    }
    resp = client.post('/api/admin/posts', json=payload, headers=admin_headers)
    assert resp.status_code == 201
    data = resp.get_json()['post']
    assert '<script>' not in data['content']
    assert '<p>正文</p>' in data['content']
