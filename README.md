# RUNOOB 博客（Flask）

从菜鸟教程 [Flask 教程](https://www.runoob.com/flask/flask-tutorial.html) 的「博客系统」各章节源码整理拼装而成，是一个完整可运行的 Flask 博客项目。

## 项目结构

```
flask-blog/
├── app/
│   ├── __init__.py          # 应用工厂 create_app() + 扩展初始化 + 后台管理
│   ├── models.py            # User / Post / Category 模型 + 收藏关联表
│   ├── forms.py             # Flask-WTF 注册/登录表单
│   ├── blueprints/
│   │   ├── main.py          # 首页（搜索/分类/分页）、关于
│   │   ├── posts.py         # 文章详情、404 错误页
│   │   ├── auth.py          # 注册、登录、登出（Flask-Login）
│   │   └── user.py          # 收藏/取消收藏、收藏列表
│   ├── templates/           # base / index / post_detail / login / register / favorites / 404
│   └── static/              # 静态文件（CSS 内联在 base.html）
├── config.py                # 配置类（dev / prod 切换）
├── wsgi.py                  # 应用入口
├── seed.py                  # 初始化数据库 + 插入测试数据
├── requirements.txt         # 依赖清单
├── Procfile                 # Railway 部署
└── .env                     # 环境变量（勿提交仓库）
```

## 快速开始

### 1. 创建虚拟环境并安装依赖

Windows：

```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Linux/macOS：

```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. 初始化数据库并插入测试数据

```
python seed.py
```

测试账号：`runoob` / `123456`

### 3. 启动开发服务器

```
flask --app wsgi run --debug
```

浏览器访问 http://127.0.0.1:5000/

- 首页 `/`：文章列表（支持搜索、分类筛选、分页）
- 文章详情 `/post/<id>`
- 注册 `/register`、登录 `/login`、登出 `/logout`
- 收藏 `/favorites`（需登录）
- 后台管理 `/admin`（Flask-Admin）

## 数据库迁移（Flask-Migrate）

修改 `models.py` 后：

```
flask --app wsgi db init        # 首次执行一次
flask --app wsgi db migrate -m "描述"
flask --app wsgi db upgrade
```

## 技术栈

Flask、Flask-SQLAlchemy、Flask-Login、Flask-WTF、Flask-Migrate、Flask-Admin、SQLite

## 部署（Railway）

推送到 GitHub 后，Railway 自动检测 `Procfile` 用 Gunicorn 启动，需在环境变量中设置 `SECRET_KEY` 和生产数据库 `DATABASE_URL`。详见菜鸟教程 [打包上线](https://www.runoob.com/flask/flask-blog-deploy.html)。

> 说明：菜鸟教程的博客教程分章节连载，官方未提供打包下载，本目录是按各章节源码拼装的完整项目；数据库章节同时介绍了「原生 SQLite + API」的写法（见 `flask-database.html`），本项目的博客主链路采用 SQLAlchemy 方案。
