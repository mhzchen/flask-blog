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
├── config.py                # 多环境配置（dev / test / prod）+ JWT / CORS / 数据库
│   ├── app/repositories.py  # 仓储层：数据库访问原语
│   ├── app/services.py      # 服务层：业务规则与组装
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
DATABASE_URL=mysql+pymysql://root:你的密码@localhost:3307/flask_blog?charset=utf8mb4
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

### 4. Docker 一键部署（推荐）

项目内置完整容器编排（`docker-compose.yml`），一次拉起全部服务：

| 服务 | 容器 | 端口 | 说明 |
|---|---|---|---|
| `db` | flaskblog-db | 3307→3306 | MySQL 8.0（utf8mb4），卷持久化 |
| `redis` | flaskblog-redis | 6379 | Redis 7（AOF 持久化），缓存/限流/Celery broker |
| `backend` | flaskblog-backend | 8000 | gunicorn 4 workers 2 threads，healthcheck 就绪 |
| `worker` | flaskblog-worker | - | Celery worker（异步任务消费） |
| `beat` | flaskblog-beat | - | Celery beat（周期调度） |
| `frontend` | flaskblog-frontend | 8080→80 | nginx 托管 Vue 构建产物 + `/api` 反代 |

```powershell
cd E:\code\python\flask-blog
# .env 需含 SECRET_KEY / JWT_SECRET_KEY（backend 容器引用）
docker compose up -d --build
```

启动流程（`docker_entrypoint.sh`）：等 MySQL 就绪 → 自动迁移建表（全新库建表+seed / 有表 stamp）→ 启动 gunicorn。

**生产化**：后端容器以非 root 用户 `appuser`（uid 1000）运行，容器被攻破也无法获得 root 权限（纵深防御）；`.dockerignore` 收紧，`tests/scripts/配置` 等非运行文件不进入镜像，镜像仅约 82MB。

访问：
- 前端：**http://localhost:8080/**（nginx 提供静态页 + 反向代理 `/api` → backend:8000）
- Swagger UI 交互文档：**http://localhost:8000/swagger**（12 个 REST 接口，含 JWT 认证可在线调试）
- OpenAPI 规范：**http://localhost:8000/openapi.json**（`/swagger` 的数据源）
- 后端健康检查：**http://localhost:8000/health**
- Prometheus 指标：**http://localhost:8000/metrics**（请求量/延迟直方图/并发/存活/Redis 缓存命中率/SQLAlchemy 连接池，可接 Grafana）

### 5. 缓存与部署验证（实测）

本仓库的缓存采用「加速层」设计（`app/cache.py`）：Redis 未配置或故障时直接放行原逻辑，绝不拖垮业务。已实测：

- **缓存命中**：`GET /api/posts` 首次 ~570ms，Redis 命中后 ~12ms（约 50 倍）；
- **缓存失效**：管理员创建文章后，`posts:*` 缓存 key 立即清除（`invalidate` 生效），下次请求回源 DB；
- **异步链路**：访问文章详情触发 `record_post_view` 任务，Celery worker 消费后浏览量落库（`views` +1），不阻塞请求；
- **限流**：`RATELIMIT_STORAGE_URI` 指向 Redis（`redis://redis:6379/2`）。

## 验证

- 后端 API 冒烟：`venv\Scripts\python scripts\verify_api.py`（19 项 API 断言，基于 MySQL seed 数据）
- 全量测试：`venv\Scripts\python -m pytest`（134 项用例，覆盖率 96.8%，含评论/点赞/限流/缓存/OpenAPI/游标分页/XSS净化/服务层单测/安全纵深/详情缓存）
- 前端：`npm run test`（Vitest 8 项：XSS 净化单测 5 + PostCard 组件测试 3）、`npm run build`（Vite 编译通过）、真实联调（5173 经代理访问 5000 返回数据）

## 性能优化

- **杜绝 N+1**：文章列表/收藏列表/后台列表接口通过 `joinedload(Post.category)` + `selectinload(Post.tags)` 一次性预加载关联，点赞数用单条 `GROUP BY` 聚合查询批量计算。实测 GET /api/posts 返回 6 篇文章只触发 4 条 SQL（优化前约 19 条，与数据量无关）。
- MySQL 全文搜索：关键词搜索走 FULLTEXT 组合索引（ngram 中文分词），SQLite 测试环境回退 LIKE。

### 压测基线（实测，`scripts/load_test.py`）

多线程并发压测后端 8000（gunicorn 4 workers/2 threads），并发 20、总量 400：

| 场景 | 吞吐 | avg | p50 | p95 | p99 | 错误率 |
|---|---|---|---|---|---|---|
| `/api/posts`（Redis 缓存命中） | **79 QPS** | 246ms | 163ms | 774ms | 1858ms | 0% |
| `/api/posts/1`（Redis 详情缓存 60s） | **54 QPS** | 351ms | 339ms | 708ms | 808ms | 0% |

**缓存是最大性能杠杆**（同负载 20 并发对比）：
- 详情页经 Redis 短 TTL 缓存（`post_detail:<id>`，60s）后，吞吐 24→**54 QPS（2.3 倍）**，p99 8.7s→**0.8s（-91%）**，尾部延迟问题基本消除；
- 详情页 per-user 的 `liked` 不进缓存、每次单查（索引，开销小），浏览量允许延迟展示；
- 文章创建/更新/删除时 `invalidate("post_detail")` 立即失效，保证读到最新。

复现：`venv\Scripts\python scripts\load_test.py --url http://localhost:8000/api/posts/1 --concurrency 20 --total 400`

## 安全纵深

- **安全响应头**（`app/security.py`）：每个响应注入 `CSP / X-Frame-Options: DENY / X-Content-Type-Options: nosniff / Referrer-Policy / Permissions-Policy`，HTTPS 下追加 `HSTS`，防点击劫持、MIME 嗅探与内容注入；`SECURITY_HEADERS_ENABLED` 可开关。
- **登录失败锁定**：连续登录失败达 `LOGIN_MAX_FAILURES`（默认 5）次，账号锁定 `LOGIN_LOCKOUT_SECONDS`（默认 300）秒，防暴力破解；生产多实例可换 Redis 做共享计数。
- **密码强度校验**：注册密码至少 8 位且同时含字母和数字，弱密码返回 422。
- **既有防护**：XSS（后端 `bleach` 净化 + 前端 DOMPurify）、JWT 双 token + 刷新、接口限流（Redis 存储）、请求参数 Pydantic 校验。

## 可观测性

- **结构化 JSON 日志**：所有应用日志（请求访问、慢查询、异常）输出为单行 JSON，含 `ts / level / logger / msg / rid / method / path / status / dur_ms / ip` 等字段，可直接接入 ELK / Datadog / 日志采集器；异常日志附带 `stack` 便于排查线上问题。
- **请求追踪**：每个请求生成 `request_id`，随响应头 `X-Request-Id` 返回，同一请求的所有日志（含慢查询）可关联检索。
- **健康检查**：`/health` 存活探针 + `/healthz` 就绪探针（校验数据库连通，供 Docker/K8s 使用）。
- **慢查询日志**：单条 SQL 超过 `SLOW_QUERY_MS`（默认 200ms）自动记录 WARNING。
- **Prometheus 指标**：`/metrics` 暴露 Prometheus 文本格式指标（请求量计数、延迟直方图、并发水位、进程存活），并在缓存层打点——**Redis 缓存命中/未命中/降级计数**（按缓存前缀），以及 **SQLAlchemy 连接池状态**（checkedout/checkedin/size），可直接被 Prometheus 抓取并接入 Grafana 做面板/告警；`METRICS_ENABLED` 控制开关（生产/开发默认开，测试关）。

## 数据库迁移

修改 `models.py` 后（配合 Flask-Migrate 管理 MySQL 结构变更）：

```
flask --app wsgi db migrate -m "描述"
flask --app wsgi db upgrade
```

> 原「服务端渲染（Jinja2 模板 + Flask-Login session）+ SQLite」版本已由本 API + Vue3 + MySQL 版本替代。