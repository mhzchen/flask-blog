"""用 Flask 测试客户端验证所有 RESTful API 端点。"""
import json
from app import create_app

app = create_app()


def req(c, method, path, token=None, json_body=None):
    headers = {'Authorization': f'Bearer {token}'} if token else {}
    return c.open(path, method=method, json=json_body, headers=headers)


results = []


def check(name, cond, detail=''):
    results.append(cond)
    print(f'[{"PASS" if cond else "FAIL"}] {name}' + (f'  {detail}' if detail else ''))


with app.test_client() as c:
    r = req(c, 'GET', '/api/categories')
    check('GET /api/categories', r.status_code == 200 and len(r.get_json()['items']) == 3)

    r = req(c, 'GET', '/api/posts')
    data = r.get_json()
    check('GET /api/posts', r.status_code == 200 and len(data['items']) == 3 and data['total'] == 3)

    r = req(c, 'GET', '/api/posts?q=flask')
    check('GET /api/posts?q=flask', len(r.get_json()['items']) == 1)

    r = req(c, 'GET', '/api/posts?category=python')
    check('GET /api/posts?category=python', len(r.get_json()['items']) == 1)

    r = req(c, 'GET', '/api/posts?page=1&per_page=2')
    data = r.get_json()
    check('分页 per_page=2', len(data['items']) == 2 and data['pages'] == 2)

    r = req(c, 'GET', '/api/posts/1')
    check('GET /api/posts/1', r.status_code == 200 and 'content' in r.get_json()['post'])

    r = req(c, 'GET', '/api/posts/999')
    check('GET /api/posts/999 -> 404', r.status_code == 404)

    r = req(c, 'POST', '/api/auth/login', json_body={'username': 'runoob', 'password': '123456'})
    login_data = r.get_json()
    check('POST /api/auth/login', r.status_code == 200 and 'access_token' in login_data)
    token = login_data.get('access_token')

    r = req(c, 'POST', '/api/auth/login', json_body={'username': 'runoob', 'password': 'wrong'})
    check('错误密码 -> 401', r.status_code == 401)

    r = req(c, 'GET', '/api/auth/me', token=token)
    check('GET /api/auth/me (带token)', r.status_code == 200 and r.get_json()['user']['username'] == 'runoob')

    r = req(c, 'GET', '/api/auth/me')
    check('未带token /me -> 401', r.status_code == 401)

    r = req(c, 'POST', '/api/favorites/1/toggle', token=token)
    check('POST 收藏 toggle', r.status_code == 200 and r.get_json()['favorited'] is True)

    r = req(c, 'GET', '/api/favorites', token=token)
    check('GET /api/favorites', r.status_code == 200 and len(r.get_json()['items']) == 1)

    r = req(c, 'GET', '/api/favorites/check/1', token=token)
    check('GET /api/favorites/check/1', r.get_json()['favorited'] is True)

    r = req(c, 'POST', '/api/favorites/1/toggle', token=token)
    check('再次toggle取消收藏', r.get_json()['favorited'] is False)

    r = req(c, 'POST', '/api/auth/register',
            json_body={'username': 'newuser', 'email': 'new@runoob.com', 'password': '123456'})
    check('POST /api/auth/register', r.status_code == 201 and 'access_token' in r.get_json())

    r = req(c, 'POST', '/api/auth/register',
            json_body={'username': 'newuser', 'email': 'x@runoob.com', 'password': '123456'})
    check('重复用户名 -> 409', r.status_code == 409)

    r = req(c, 'POST', '/api/auth/register', json_body={'username': '', 'email': '', 'password': ''})
    check('空字段注册 -> 400', r.status_code == 400)

    r = c.open('/api/posts', method='OPTIONS', headers={
        'Origin': 'http://localhost:5173',
        'Access-Control-Request-Method': 'GET'
    })
    check('OPTIONS 预检含 CORS 头', 'access-control-allow-origin' in {k.lower(): v for k, v in r.headers.items()})

print(f'\n总体结果：{sum(results)}/{len(results)} 通过')