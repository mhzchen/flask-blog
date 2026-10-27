"""用 Flask 测试客户端验证各路由可访问（含 CSRF token 处理）。

预期按真实行为设定：
- 未登录访问 /favorites 会 302 重定向到登录页
- 已登录用户访问 /register、/login 会 302 重定向回首页
- /admin 无尾部斜杠会 308 重定向到 /admin/
"""
import re
from app import create_app

app = create_app()


def get_csrf(html):
    m = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html)
    return m.group(1) if m else None


def check(method, path, expect_code, expect_text, client):
    resp = client.open(path, method=method)
    body = resp.get_data(as_text=True)
    ok_code = resp.status_code == expect_code
    ok_text = (expect_text is None) or (expect_text in body)
    status = 'PASS' if (ok_code and ok_text) else 'FAIL'
    print(f'[{status}] {method} {path} -> {resp.status_code} (期望 {expect_code}, 含"{expect_text}")')
    return status == 'PASS'


results = []

# ---------- 未登录（匿名） ----------
anon = app.test_client()
results.append(check('GET', '/favorites', 302, None, anon))      # 未登录应跳登录页
results.append(check('GET', '/register', 200, '注册', anon))
results.append(check('GET', '/login', 200, '登录', anon))

# ---------- 登录 ----------
login_html = anon.get('/login').get_data(as_text=True)
csrf = get_csrf(login_html)
assert csrf, '未提取到 CSRF token'
anon.post('/login',
          data={'csrf_token': csrf, 'username': 'runoob', 'password': '123456'})

# ---------- 已登录（匿名客户端已登录，cookie 保持） ----------
results.append(check('GET', '/', 200, '最新文章', anon))
results.append(check('GET', '/about', 200, '关于本站', anon))
results.append(check('GET', '/post/1', 200, 'Flask 入门完全指南', anon))
results.append(check('GET', '/register', 302, None, anon))       # 已登录访问注册→跳首页
results.append(check('GET', '/login', 302, None, anon))          # 已登录访问登录→跳首页
results.append(check('GET', '/favorites', 200, '我的收藏', anon))
results.append(check('GET', '/?q=flask', 200, '最新文章', anon))
results.append(check('GET', '/?category=flask', 200, '最新文章', anon))
results.append(check('GET', '/admin/', 200, 'RUNOOB 博客后台', anon))
results.append(check('GET', '/nonexistent', 404, '404', anon))

# ---------- 收藏流程 ----------
detail_html = anon.get('/post/1').get_data(as_text=True)
fav_csrf = get_csrf(detail_html)
fav_resp = anon.post('/favorite/1', data={'csrf_token': fav_csrf}, follow_redirects=False)
fav_ok = fav_resp.status_code == 302
print(f'[{"PASS" if fav_ok else "FAIL"}] POST /favorite/1 -> {fav_resp.status_code} (期望 302)')
results.append(fav_ok)

favs = anon.get('/favorites').get_data(as_text=True)
has_post = 'Flask 入门完全指南' in favs
print(f'[{"PASS" if has_post else "FAIL"}] 收藏列表包含文章')
results.append(has_post)

print('\n总体结果：' + ('全部通过' if all(results) else f'存在失败项（{results.count(False)} 项）'))
