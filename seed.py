"""向数据库插入测试数据（建表由 Alembic 迁移负责）。

用法：
    1) 先执行迁移建表：flask --app wsgi db upgrade
    2) 再执行本脚本补数据：python seed.py
仅在数据库没有用户数据时执行，可重复运行。
"""
from app import create_app, db
from app.models import Category, Post, User

app = create_app()

with app.app_context():
    if User.query.count() > 0:
        print('数据库已有数据，跳过 seed。')
        raise SystemExit(0)

    # 1. 创建用户（密码：123456）
    admin = User(username='runoob', email='admin@runoob.com', is_admin=True)
    admin.set_password('123456')
    db.session.add(admin)

    # 2. 创建分类
    py_cat = Category(name='Python', slug='python')
    css_cat = Category(name='CSS', slug='css')
    flask_cat = Category(name='Flask', slug='flask')
    db.session.add_all([py_cat, css_cat, flask_cat])
    db.session.commit()

    # 3. 创建文章
    post1 = Post(
        title='Flask 入门完全指南',
        slug='flask-beginner-guide',
        summary='从零开始学习 Flask，涵盖路由、模板、ORM 等核心概念。',
        content='<h2>为什么学 Flask？</h2><p>Flask 是 Python 最灵活的 Web 微框架...</p>',
        category=flask_cat,
    )
    post2 = Post(
        title='Python 协程详解',
        slug='python-coroutine',
        summary='一文搞懂 asyncio、协程、事件循环。',
        content='<h2>什么是协程？</h2><p>协程是一种比线程更轻量的并发方案...</p>',
        category=py_cat,
    )
    post3 = Post(
        title='CSS Grid 布局实战',
        slug='css-grid-layout',
        summary='用 CSS Grid 轻松实现复杂的响应式布局。',
        content='<h2>Grid 入门</h2><p>Grid 是二维布局系统...</p>',
        category=css_cat,
    )
    db.session.add_all([post1, post2, post3])
    db.session.commit()

    print('数据库初始化完成！')
    print('登录账号：runoob / 123456')