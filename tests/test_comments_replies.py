"""评论嵌套（回复）+ 分页测试"""
from app import db
from app.models import Comment


def _reply_count(post_id, parent_id):
    return Comment.query.filter_by(post_id=post_id, parent_id=parent_id).count()


def test_reply_to_comment(client, post, user_headers):
    r1 = client.post(f'/api/posts/{post.id}/comments', headers=user_headers, json={'content': '顶层评论'})
    assert r1.status_code == 201
    top_id = r1.get_json()['comment']['id']

    r2 = client.post(f'/api/posts/{post.id}/comments', headers=user_headers,
                     json={'content': '回复内容', 'parent_id': top_id})
    assert r2.status_code == 201
    assert r2.get_json()['comment']['parent_id'] == top_id

    rl = client.get(f'/api/posts/{post.id}/comments')
    data = rl.get_json()
    assert len(data['items']) == 1
    assert data['items'][0]['id'] == top_id
    assert len(data['items'][0]['replies']) == 1
    assert data['items'][0]['replies'][0]['content'] == '回复内容'


def test_reply_to_reply_denormalized(client, post, user_headers):
    top = client.post(f'/api/posts/{post.id}/comments', headers=user_headers, json={'content': 'top'}).get_json()['comment']
    r1 = client.post(f'/api/posts/{post.id}/comments', headers=user_headers, json={'content': 'r1', 'parent_id': top['id']}).get_json()['comment']
    r2 = client.post(f'/api/posts/{post.id}/comments', headers=user_headers, json={'content': 'r2', 'parent_id': r1['id']}).get_json()['comment']
    assert r2['parent_id'] == top['id']


def test_reply_to_missing_comment_400(client, post, user_headers):
    resp = client.post(f'/api/posts/{post.id}/comments', headers=user_headers,
                       json={'content': 'x', 'parent_id': 9999})
    assert resp.status_code == 400


def test_comments_pagination(client, post, user_headers):
    for i in range(3):
        client.post(f'/api/posts/{post.id}/comments', headers=user_headers, json={'content': f'c{i}'})
    r = client.get(f'/api/posts/{post.id}/comments?per_page=1')
    data = r.get_json()
    assert data['total'] == 3
    assert data['pages'] == 3
    assert len(data['items']) == 1