# RUNOOB 博客（前后端分离版）

从菜鸟教程 [Flask 教程](https://www.runoob.com/flask/flask-tutorial.html) 的「博客系统」出发，重构为 **前后端分离** 架构：Flask 提供纯 RESTful API（JWT 认证），前端用 **Vue3 + Vite + Pinia** 重写，数据库采用 **MySQL**。

## 技术栈

| 端 | 技术 |
|---|---|
| 后端 | Flask、Flask-SQLAlchemy、Flask-Migrate、Flask-JWT-Extended、Flask-CORS、MySQL |
| 前端 | Vue3、Vite、Vue Router、Pinia、Axios |

## 项目结构

```
flask-blog/
├── app/
│   ├── __init__.py          # 应用工厂：db / migrate / jwt / cors + 注册 API 蓝图
│   ├── models.py            # User / Post / Category 模型 + 收藏关联表（含 to_dict）
│   └── api/                 # RESTful API 蓝图
│       ├── auth.py          # 注册、登录、当前用户（JWT）
│       ├── posts.py         # 文章列表(搜索/分类/分页)、详情
│       ├── categories.py    # 分类列表
│       ├── favorites.py     # 收藏列表、切换收藏、检查收藏状态
│       └── admin.py         # 后台：文章/分类增删改查（需管理员）
├── frontend/                # Vue3 前端（Vite）
│   ├── src/
│   │   ├── api/index.js     # Axios 实例（token 拦截器 + 401 跳转）
│   │   ├── stores/auth.js   # Pinia 认证 store（token 存 localStorage）
│   │   ├── router/index.js  # 路由 + 登录守卫
│   │   ├── components/      # NavBar / PostCard
│   │   └── views/           # Home / PostDetail / Login / Register / Favorites / Admin
│   ├── vite.config.js       # 开发代理 /api → localhost:5000
│   └── package.json
├── config.py                # 配置类（dev / prod）+ JWT / CORS / 数据库
├── wsgi.py                  # 后端入口
├── seed.py                  # 初始化 MySQL 数据库 + 测试数据
├── requirements.txt
├── Procfile
└── .env                     # 环境变量（含 DATABASE_URL）
```

## API 一览

| 方法 | 路径 | 说明 | 认证 |
|---|---|---|---|
| POST | `/api/auth/register` | 注册，返回 token | 否 |
| POST | `/api/auth/login` | 登录，返回 token | 否 |
| GET | `/api/auth/me` | 当前用户信息 | JWT |
| GET | `/api/categories` | 分类列表 | 否 |
| GET | `/api/posts?q=&category=&page=` | 文章列表（搜索/分类/分页） | 否 |
| GET | `/api/posts/<id>` | 文章详情（含正文） | 否 |
| GET | `/api/favorites` | 我的收藏 | JWT |
| POST | `/api/favorites/<id>/toggle` | 切换收藏 | JWT |
| GET | `/api/favorites/check/<id>` | 检查是否已收藏 | JWT |
| GET | `/api/admin/posts` | 后台文章列表 | 管理员 |
| POST | `/api/admin/posts` | 新建文章 | 管理员 |
| PUT | `/api/admin/posts/<id>` | 更新文章 | 管理员 |
| DELETE | `/api/admin/posts/<id>` | 删除文章 | 管理员 |
| POST/PUT/DELETE | `/api/admin/categories[/<id>]` | 分类增删改 | 管理员 |

## 快速开始

### 0. 准备 MySQL

确保本机 MySQL 已运行，并创建数据库：

```sql
CREATE DATABASE IF NOT EXISTS flask_blog
  DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

在项目根目录的 `.env` 中配置数据库连接（已默认指向本机 `flask_blog` 库，按需改密码）：

```
DATABASE_URL=mysql+pymysql://root:你的密码@localhost:3306/flask_blog?charset=utf8mb4
```

### 1. 后端

```powershell
cd E:\code\python\flask-blog
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python seed.py                 # 在 MySQL 建表 + 插入测试数据
flask --app wsgi run --debug   # 启动后端，端口 5000
```

测试账号：`runoob` / `123456`

### 2. 前端

```powershell
cd E:\code\python\flask-blog\frontend
npm install
npm run dev                    # 启动 Vite，端口 5173
```

浏览器访问 **http://localhost:5173/** 。开发模式下 `/api` 请求由 Vite 代理到后端 `localhost:5000`，无需手动配置跨域。

后台管理：用管理员账号 `runoob` 登录后，导航栏出现「后台管理」，进入 `/admin` 管理文章和分类。

### 3. 生产构建（可选）

```powershell
cd frontend
npm run build                  # 产物输出到 frontend/dist/
```

## 验证

- 后端：`venv\Scripts\python verify_api.py`（19 项 API 断言，全通过，基于 MySQL）
- 前端：`npm run build`（Vite 编译通过）、真实联调（5173 经代理访问 5000 返回数据）

## 数据库迁移

修改 `models.py` 后（配合 Flask-Migrate 管理 MySQL 结构变更）：

```
flask --app wsgi db migrate -m "描述"
flask --app wsgi db upgrade
```

> 原「服务端渲染（Jinja2 模板 + Flask-Login session）+ SQLite」版本已由本 API + Vue3 + MySQL 版本替代。