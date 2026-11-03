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
- **异步链路**：访问文章详情触发 `record_post_view` 任务，Celery worker 消费后浏览量落库（`views` +1），不阻塞请求；DB 瞬时连接错误按指数退避自动重试（2/4/8s，最多 3 次），重试耗尽仍失败则进死信队列（Redis `task_deadletter`，可追溯排查）；同一文章 120s 窗口内幂等去重（Redis SETNX，`view_dedup:<id>`），窗口内重复投递自动跳过防重复计数；任务全局超时保护（硬 60s/软 50s）；broker 不可达自动降级为同步执行，功能不丢；
- **限流**：`RATELIMIT_STORAGE_URI` 指向 Redis（`redis://redis:6379/2`）；
- **防雪崩**：所有缓存 TTL 加 ±20% 随机抖动（`CACHE_DETAIL_TIMEOUT` 基数），避免大量 key 同时过期集中打穿 DB；
- **防穿透**：不存在的文章 id 也会写短 TTL 空标记（`CACHE_NEGATIVE_TIMEOUT`，默认 30s），命中即 404 且不再打 DB，恶意/误请求不拖垮数据库。

## 验证

- 后端 API 冒烟：`venv\Scripts\python scripts\verify_api.py`（19 项 API 断言，基于 MySQL seed 数据）
- 全量测试：`venv\Scripts\python -m pytest`（157 项用例，覆盖率 94.38%，含评论/点赞/限流/缓存/OpenAPI/游标分页/XSS净化/服务层单测/安全纵深/详情缓存/metrics 缓存打点与连接池/Celery 重试与幂等去重/死信/JWT 登出黑名单/日志慢请求采样）
- 前端：`npm run test`（Vitest 8 项：XSS 净化单测 5 + PostCard 组件测试 3）、`npm run build`（Vite 编译通过）、真实联调（5173 经代理访问 5000 返回数据）

### CI 流水线（`.github/workflows/ci.yml`）

- **lint-typecheck**：ruff + mypy + 安全扫描（`bandit -r app -c .bandit` + `pip-audit -r requirements.txt`）（setup-python 自带 pip 缓存）
- **test**：Python 3.11/3.12/3.13 矩阵跑全量 pytest（覆盖率门槛 90%），setup-python 自带 pip 缓存
- **frontend**：setup-node + `npm ci --legacy-peer-deps`（兼容 vite5/vitest）+ `npm run test`（Vitest 8 项）+ `npm run build`（Vite 生产构建验证）+ `npm audit --omit=dev --audit-level=high`（生产依赖漏洞门禁），npm 依赖缓存
- **DB Migration (MySQL)**：干净 MySQL 库跑 `flask db upgrade` 建全表，并校验建出的表与模型元数据一致（防迁移/模型漂移）

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
- **登录失败锁定**：连续登录失败达 `LOGIN_MAX_FAILURES`（默认 5）次，账号锁定 `LOGIN_LOCKOUT_SECONDS`（默认 300）秒，防暴力破解；失败计数默认存 Redis（`LOGIN_REDIS_ENABLED`，多 worker/多实例共享，锁定才不被分拆请求绕过），Redis 不可用自动降级为进程内计数。
- **密码强度校验**：注册密码至少 8 位且同时含字母和数字，弱密码返回 422。
- **JWT 登出黑名单**（`app/jwt_blacklist.py`）：`POST /api/auth/logout` 把当前 token 的 `jti` 写入 Redis 黑名单（TTL = 剩余有效期，自动过期），之后该 token 访问立即 401；`POST /api/auth/password` 改密后写入用户级撤销时间戳，该用户所有旧 token（含 refresh）即时失效需重新登录；Redis 不可用时降级放行（认证不因黑名单服务故障中断）。
- **既有防护**：XSS（后端 `bleach` 净化 + 前端 DOMPurify）、JWT 双 token + 刷新、接口限流（Redis 存储）、请求参数 Pydantic 校验。

## 可观测性

- **结构化 JSON 日志**：所有应用日志（请求访问、慢查询、异常）输出为单行 JSON，含 `ts / level / logger / msg / rid / method / path / status / dur_ms / ip` 等字段，可直接接入 ELK / Datadog / 日志采集器；异常日志附带 `stack` 便于排查线上问题。
- **请求追踪**：每个请求生成 `request_id`，随响应头 `X-Request-Id` 返回，同一请求的所有日志（含慢查询）可关联检索。
- **健康检查**：`/health` 存活探针 + `/healthz` 就绪探针（校验数据库连通，供 Docker/K8s 使用）。
- **慢查询日志**：单条 SQL 超过 `SLOW_QUERY_MS`（默认 200ms）自动记录 WARNING，并带当前 `request_id`（`rid`），可串联到具体请求定位；
- **慢请求采样**：整请求超过 `SLOW_REQUEST_MS`（默认 1000ms）按 `SLOW_REQUEST_SAMPLE_RATE`（默认全量 1.0，高流量可调低）额外记录 `slow_request` WARNING（区别于所有请求的 INFO `req` 行），用于精准抓慢请求。
- **Prometheus 指标**：`/metrics` 暴露 Prometheus 文本格式指标（请求量计数、延迟直方图、并发水位、进程存活），并在缓存层打点——**Redis 缓存命中/未命中/降级计数**（按缓存前缀），以及 **SQLAlchemy 连接池状态**（checkedout/checkedin/size），可直接被 Prometheus 抓取并接入 Grafana 做面板/告警；`METRICS_ENABLED` 控制开关（生产/开发默认开，测试关）。

## 数据库迁移

生产用 Flask-Migrate（Alembic）版本化管理 MySQL 结构，迁移链 `migrations/versions/`：0001 初始建表 → 0007 评论父级。全新库 `flask db upgrade` 建全表 + seed；已有表但无迁移记录则 `flask db stamp head` 认领。修改 `models.py` 后：

```
flask --app wsgi db migrate -m "描述"
flask --app wsgi db upgrade
```

迁移已做**跨方言兼容**：全文索引（FULLTEXT + ngram）与索引存在性检查按方言处理（MySQL 用 information_schema，SQLite 用 sqlite_master；FULLTEXT 仅 MySQL 创建），保证 dev(SQLite)/prod(MySQL) 迁移链一致。CI 含独立 **DB Migration (MySQL)** job：在干净 MySQL 库跑 `flask db upgrade`，并校验建出的表与模型元数据一致（防迁移/模型漂移）。迁移使用 Alembic **batch mode**（`batch_alter_table`，约束须命名）处理 SQLite 方言不支持的 ALTER，dev(SQLite)/prod(MySQL) 均可从 0001 一路跑到 0007 全链，并可 downgrade 回退。

> 原「服务端渲染（Jinja2 模板 + Flask-Login session）+ SQLite」版本已由本 API + Vue3 + MySQL 版本替代。


## 本轮：#36 OpenTelemetry 全链路追踪 / #37 CI 发布镜像 + 蓝绿回滚 / #38 DB 读写分离 / #39 前端组合式 API + Pinia + 骨架屏

- **#36 OpenTelemetry 全链路追踪**：新增 `app/telemetry.py`，按 `OTEL_EXPORTER_OTLP_ENDPOINT` 走 OTLP 或 ConsoleSpanExporter，对 Flask / SQLAlchemy / Redis / Celery 做 instrumentation（一条 HTTP→DB→Redis→Celery 的 trace）；请求 JSON 日志通过 `_JsonFormatter` 注入 `trace_id`（与 span 同一 trace_id 贯穿）。`OTEL_ENABLED` 开关控制、`_initialized` 幂等；requirements.txt 补 6 行 OTel 依赖。容器真验：`/api/posts/1` 日志 `"trace_id":"5f30735d…"` 与 ConsoleSpanExporter 多条 `SpanData` 的 `trace_id:0x5f30735d…` 完全一致。用例：`tests/test_telemetry.py`（3 项：无 span 返回 None / TestingConfig 关闭 / init 幂等）。
- **#37 CI 发布 Docker 镜像 + 蓝绿回滚**：`.github/workflows/ci.yml` 新增 `publish-docker` job（needs 全部 4 个 job、仅 main push、GHCR login + metadata-action tags sha-+latest、push backend 与 frontend 镜像）；新增 `scripts/deploy-bluegreen.ps1`（读 `.bluegreen.state` 取 active → docker run 目标色容器 blue=8001/green=8002 → 轮询 `/health` 就绪（≤60s，失败删容器保 active）→ 写 state + 停旧容器；`-Rollback` 反向切回）。本地真验：`deploy` active=blue→green、`-Rollback`→blue 均成功，state 文件随之切换。
- **#38 性能 DB 读写分离 + 连接池按角色拆分**：新增 `app/dbrouting.py` 的 `RoutingSession`（写/flush 固定走 default 主库，读在配置 slave 时走从库，无 slave 回落主库）；config 用 `DATABASE_URL_SLAVE` 生成 `SQLALCHEMY_BINDS={'slave':…}`（None 时空 dict 兜底），slave 独立 engine = 独立连接池（沿用池配置）。容器真验：带 `DATABASE_URL_SLAVE` 启动 `engines=['slave', None]`、读查询正常。用例：`tests/test_dbrouting.py`（3 项：读走 slave / 写走主库 / 无 slave 回落主库）。
- **#39 前端组合式 API + Pinia 模块化 + 骨架屏**：新增 `frontend/src/stores/posts.js`（文章列表域 Pinia store：items/total/pages/hasPrev/hasNext/page/loading/categories/tags + fetchList/fetchCategories/fetchTags）；`HomeView.vue` 改用 `storeToRefs(store)`（删除本地 fetch 逻辑，保留筛选/翻页调 store）；`PostDetailView.vue` 加 `loadingPost` + skeleton-pulse 骨架屏（`v-if="loadingPost"` 6 条 skeleton-line）。验证：vitest **8 passed**（sanitize 5 + PostCard 3）、`npm run build` 成功。


## 本轮：#40 前端路由懒加载+Pinia持久化+Web Vitals / #41 Grafana+Prometheus告警+OTLP / #42 Celery Beat定时调度+失败告警webhook

- **#40 前端：路由懒加载 + Pinia 持久化 + Web Vitals**：路由 6 个 view 均保持动态 import（Vite 自动分包各 view），并在 `vite.config.js` 加 `build.rollupOptions.output.manualChunks` 拆出独立 `vue-vendor`（vue/vue-router/pinia，~99KB）与 `axios`（~59KB）vendor chunk，主包更小、缓存复用更好；`frontend/src/stores/posts.js` 的筛选态（keyword/categorySlug/tagName/page）经 `_persistFilter()` 持久化到 localStorage（`posts_filter`），state 初始化自动恢复，刷新/重进保持筛选与页码；新增 `web-vitals` 依赖，`main.js` 采集 CLS/FCP/INP/LCP/TTFB，经 `sendBeacon` 异步上报后端 `POST /api/vitals`（页面卸载也能送达），后端新增 `/api/vitals` 端点记 INFO 日志。验证：`npm run build` 分包成功（vue-vendor/axios 独立 chunk + 各 view 懒加载 chunk），vitest 8 passed。

- **#41 可观测性：Grafana 面板 + Prometheus 告警 + OTLP 采集**：新增 `monitoring/`——`prometheus.yml`（scrape backend:8000 /metrics，15s）、`rules.yml` 三条告警（BackendDown `up==0` / High5xxErrorRate 5xx rate>0.05·5m / HighInflight 并发>50）、`otel-collector.yml`（otlp/http:4318→debug exporter）、`grafana/provisioning/`（Prometheus 数据源 uid=Prometheus + dashboard provider）、`grafana/dashboards/flask-overview.json`（uid=flask-overview，7 面板：QPS/P95延迟/并发/缓存命中未命中/DB连接池/5xx计数/5xx率阈值0.05）；`docker-compose.yml` 新增 prometheus(9090)/grafana(3000, admin/admin)/otel-collector(4318) 三服务 + `grafana_data` volume，backend 注入 `OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318`，worker/beat 注入 `BACKEND_INTERNAL_URL=http://backend:8000`。验证：`docker compose config --quiet` 通过、dashboard JSON 与 5 个 YAML 语法校验通过；**容器启动受阻**——Docker Hub 当前网络不可达（grafana/prom/otel 三镜像 pull 超时、本地无镜像），监控栈未能拉起，待网络恢复后 `docker compose up -d prometheus grafana otel-collector` 启动并人工验证 9090/3000/4318。

- **#42 异步：Celery Beat 定时调度 + 失败告警 webhook**：`celery_app.py` beat_schedule 扩为 3 个周期任务（heartbeat-every-minute 60s / warm-hot-cache-2min 120s / prune-deadletter-hourly 3600s）；新增 `tasks.warm_hot_cache`（urllib 请求 `BACKEND_INTERNAL_URL` 的 /api/posts、/api/posts/1~3 预热热点缓存）与 `tasks.prune_deadletter`（ltrim 死信列表到 `DEADLETTER_MAX`）；新增 `_register_failure_webhook` 幂等注册 `task_failure` 信号，任务失败 POST JSON 到 `ALERT_WEBHOOK_URL`（默认 `http://backend:8000/api/internal/alerts`），推送失败静默不影响 worker；后端新增 `POST /api/internal/alerts` 模拟告警接收端（记 `alert_received` WARNING 日志）。容器真验：beat 日志 `Sending due task warm-hot-cache-2min`、worker 注册 warm/prune、backend 收到预热 GET /api/posts 200、失败任务触发 task_failure 后 backend 收到 `alert_received`（webhook 闭环验证通过）。

## 本轮：#43 监控栈补齐验证 / #44 链路可视化 / #45 前端纵深 / #46 部署生产化 / #47 异步可靠性深化 / #48 数据库巡检

- **#48 数据库巡检（EXPLAIN 基线 + 冗余索引 + 主从一致性）**：新增 `scripts/db_audit.py` —— 直连 MySQL 巡检 9 张表，输出 7 条核心查询的 EXPLAIN 基线 + 索引清单 + FULLTEXT 冗余自动检测，支持 `--slave <dsn>` 对比主从各表行数一致性，报告落 `reports/db-audit.md`。运行检出 `ix_posts_content_fulltext`（content 单列 FULLTEXT）被 `ix_posts_search_fulltext`（title+summary+content ngram）完全覆盖、`ix_posts_title` 无精确/前缀查询命中，落地删除：`app/models.py` 移除该 FULLTEXT Index 定义、title 列 `index=True`→`index=False`；新增迁移 `migrations/versions/0008_drop_redundant_indexes.py`（batch 安全、SQLite/MySQL 双方言判断），`flask db upgrade` 0007→0008 成功。MySQL 复核 posts 现存索引 = PRIMARY / slug(唯一) / ix_posts_category_id / ix_posts_created_at / ix_posts_search_fulltext，两个冗余索引已删。
- **#47 异步可靠性深化（队列隔离 + 分布式锁 + 死信告警）**：`app/celery_app.py` 加 `task_routes`（warm_hot_cache / prune_deadletter → critical 队列）；`app/tasks.py` 新增 `task_lock()`（Redis SETNX TTL90 分布式锁，warm_hot_cache 防多 worker 重入）与 `_send_alert()`（复用 ALERT_WEBHOOK_URL），prune_deadletter 死信剩余 ≥ DEADLETTER_MAX×80% 时发 `deadletter_high` 告警；`docker-compose.yml` worker 命令改 `-Q critical,default` 并新增独立 `worker-critical` 服务（`-Q critical --concurrency=2`）。真验：worker-critical 仅消费 critical、worker 消费 critical+default；注入 90 条死信 → `celery call tasks.prune_deadletter` → backend 收到 `alert_received` + `POST /api/internal/alerts 200`；连续两次 warm_hot_cache，第二次日志「已有实例在执行预热，本次跳过」（锁生效）。测试后清理了 task_deadletter / task_lock 测试数据。
- **#45 前端纵深（PWA + LCP + Web Vitals 可视化）**：新增 `frontend/src/utils/vitals.js`（web-vitals 聚合入 localStorage `web_vitals_history`，上限 40 条）、`frontend/public/sw.js`（PWA：静态 cache-first、`/api/*` 网络优先离线回退、SPA 兜底 index.html）、`frontend/src/views/VitalsView.vue`（`/vitals` 页：按指标分组 SVG 折线 + 最新值/评级/平均）；`main.js` 接入 `recordVitals` + 仅 `import.meta.env.PROD` 注册 SW；`router/index.js` 首页改静态 import（首屏直达+LCP）、`requestIdleCallback` 预取 PostDetail/Login chunk、新增 `/vitals` 路由。验证：npm build 6.95s 成功（dist 含 sw.js、VitalsView 独立 chunk）、vitest 8 passed；frontend 容器 force-recreate 后 `http://localhost:8080/sw.js` HTTP 200（len 1706）、`/vitals` 200 且为 index.html（SPA 路由）。
- **#46 部署生产化（资源限额 + 镜像扫描 + 自动回滚）**：新建 `docker-compose.override.yml`（backend/worker/worker-critical 各 1.0 CPU+512M/384M，beat/db/redis/frontend/prom/grafana/otel 0.5~1.0 CPU+256M/512M，`docker compose config` 真验 deploy.limits 已合并生效）；`scripts/deploy-bluegreen.ps1` 加 `-RollbackOnFailure`（就绪探针失败→下线新色、保持旧 active 即自动回滚）；`.github/workflows/ci.yml` 追加 `trivy-scan` job（aquasecurity/trivy-action，CRITICAL/HIGH exit-code=1 门禁，`needs: publish-docker`）与 `deploy-bluegreen` job（`needs: [publish-docker, trivy-scan]`，secrets 需配 DEPLOY_HOST/DEPLOY_USER/DEPLOY_SSH_KEY）；新建 `k8s/hpa.yaml`（CPU 60%/MEM 70%，min2/max8，scaleDown 稳定窗口 300s，预演清单）。CI YAML 解析确认 jobs 含 trivy-scan/deploy-bluegreen，ps1 语法 0 错误；trivy 本体需 Docker Hub 网络恢复后于 CI 运行。
- **#43 监控栈补齐验证**：新增 `scripts/monitoring-up.ps1` 一键启用脚本（`docker compose up -d prometheus grafana otel-collector`）+ 5 项验证清单（Grafana 3000 admin/admin 面板、prom 9090 targets、告警 FlaskBackendDown 触发法、OTLP 链路落盘、容器状态）。**受 Docker Hub 网络不可达阻塞**：prom/grafana/otel 三镜像无本地副本无法拉起，监控栈待网络恢复后运行该脚本一键启用。
- **#44 链路可视化（离线瀑布 + OTLP 落盘）**：`monitoring/otel-collector.yml` 的 traces pipeline 同时 export debug + file（file exporter 落 `/tmp/traces.json`），compose 挂载 `./monitoring/traces`；新增 `scripts/trace_report.py` 离线瀑布查看器（解析 traces.json → 按 trace 分组 → 渲染 HTTP→DB→Redis→Celery span 瀑布，输出 `reports/trace-report.html`）。当前 spans=0（collector 未启动），网络恢复后产生请求即有真实瀑布。已知限制：`SQLAlchemyInstrumentor only instruments "sqlalchemy >= 1.0.0, < 2.1.0"`（实际 2.1.6，DB span 未插桩），属依赖兼容，需网络升级 instrumentation 库（或改 dbapi 插桩）后消除。

- **质量门**：全量 pytest 173 passed、覆盖率 90.51%（≥90 门禁达标）；ruff check（app/tests/scripts）通过；mypy（app，24 文件）通过。

## 本轮：#49 前端 E2E 测试（Playwright 真实链路）/ #50 Redis 持久化 + 高可用

- **#49 前端 E2E（Playwright 端到端真实浏览器链路）**：基于已有 `@playwright/test` 骨架补全真实业务链路——`e2e/workflow.spec.js` 新增 搜索过滤（首页关键词→结果）、发帖（登录 runoob → /admin 新建文章 → 回首页搜索可见）、评论（登录 → 打开文章 → 发表评论 → 可见）3 条链路用例，与 `e2e/app.spec.js` 首页/详情/登录共 6 条。`playwright.config.js` 按 `process.env.CI` 分流：本地用系统 Edge channel（免下载浏览器）、CI 用自带 chromium；首页/搜索首查 timeout 提至 30s（PWA 冷启动）。验证：本地 `npm run e2e` 6 passed（约 1.1m），vitest 8 passed 无回归；测试产生的 E2E 文章/评论已清理。CI 新增 `e2e` job（needs frontend）：docker compose 起 db/redis/backend/frontend → `flask db upgrade` + `python seed.py` 播种 → `npx playwright test` 跑真实浏览器链路。
- **#50 Redis 持久化 + 高可用**：确认并强化 Redis 持久化——compose 原已配 `appendonly yes` + `redis_data` volume，本轮改为配置文件驱动 `redis/redis.conf`（AOF everysec + RDB 快照 save 900/300/60 + `maxmemory 256mb` + `maxmemory-policy allkeys-lru` + tcp-keepalive），compose redis `command: redis-server /usr/local/etc/redis/redis.conf` + 挂载 conf。真验：config_file 指向 conf、`aof_enabled:1`、`maxmemory 256.00M`/`allkeys-lru` 生效；写 key → `docker restart` → 数据保留（AOF/RDB 双持久化）。高可用：提供 `redis/sentinel.conf`（Redis Sentinel 主从 + 自动故障转移模板，3 节点 2 哨兵多数派），说明单机 compose 不启用（同机无真实故障隔离价值）、生产 3 机部署时启用。


## 本轮：#51 接口版本化 / #52 统一异常与错误码 / #53 Flask async 视图 / #54 WebSocket 实时推送

- **#51 接口版本化**：全路由从 `/api` 改为 `/api/v1`——`app/__init__.py` 蓝图前缀、`app/openapi.py`（PATHS）、`app/tasks.py`（预热请求）、前端 `frontend/src/api/index.js`（baseURL + refresh 路径）、`tests/` 16 个文件批量替换。版本策略：路由前缀固定 `v1`，后续新版本以 `v2` 前缀并存迁移，无版本号请求一律 404（提示客户端需显式带版本）。真验：旧路径 `/api/posts` → 404、`/api/v1/posts` → 200；pytest 子集 64 passed（posts/auth/errors/openapi/comments/admin/tags/categories，覆盖率门禁需全量）。
- **#52 统一异常与错误码**：重写 `app/errors.py`——新增 `ErrorCode` 业务错误码枚举（VALIDATION_ERROR/UNAUTHORIZED/TOKEN_EXPIRED/FORBIDDEN/NOT_FOUND/METHOD_NOT_ALLOWED/CONFLICT/RATE_LIMITED/UNSUPPORTED_VERSION/INTERNAL_ERROR）、`_HTTP_TO_CODE` HTTP 状态→业务码映射、`AppError` 业务异常类、`_envelope()` 统一响应结构 `{code, status:'error', error_code, message, error, trace_id, path, errors?}`，全局 handler 三分支（HTTPException / AppError / Exception）。保留 `code`（HTTP 状态）与 `error`（message 别名）兼容旧客户端与既有测试。真验：不存在资源返回 404 完整 envelope（含 error_code/trace_id）。
- **#53 Flask async 视图**：新建 `app/api/system.py`，`@system_bp.get('/status')` async 视图，用 `asyncio.gather + asyncio.to_thread` 并发探查 DB / Redis / Celery broker 三项延迟（异步并发收益演示）。需安装 `asgiref`（Flask async extra）——缺失时报 `Install Flask with the 'async' extra in order to use async views.`。真验：HTTP 200，`checks` 三项、`total_ms` 趋近最慢一项（三者之和≈8600ms，实际 4305ms，并发生效）；生产真正并发收益在 ASGI server（hypercorn）下体现，gunicorn(WSGI) 自动桥接、功能同样可用。
- **#54 WebSocket 实时推送**：后端新建 `app/socketio.py`（Flask-SocketIO，async_mode='threading' + connect/disconnect + `emit_comment_new`/`emit_post_new` 广播），`create_app` 集成 `socketio.init_app`；`create_comment` 成功后广播 `comment:new`。前端安装 `socket.io-client`，新建 `frontend/src/utils/realtime.js`（connectSocket/disconnectSocket）、`App.vue` 接入顶部实时通知条（comment:new/post:new 展示 3s）、`frontend/nginx.conf` 加 `/socket.io/` WebSocket 反代（Upgrade 头）。真验：`socketio.run(..., allow_unsafe_werkzeug=True)` 起 5001，socketio 客户端连 `ws://127.0.0.1:5001` → 登录 runoob → 发表评论 → 客户端实际收到 `comment:new` 广播（threading 单进程有效）。生产注意：多 worker / 多实例广播需配置 redis message queue 适配器（`SocketIO.AsyncRedisManager`），且后端需以 ASGI server（hypercorn）挂载 socketio 才能对外提供 `/socket.io` 端点。
