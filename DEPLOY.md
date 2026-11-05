# 生产部署指南（DEPLOY.md）

从零把这个博客部署到一台公网 Linux 服务器的完整步骤。

## 1. 前置要求

| 项 | 最低配置 | 推荐 |
|---|---|---|
| 服务器 | 2 核 4G / 40G 磁盘 | 4 核 8G / 100G SSD |
| 系统 | Ubuntu 22.04 LTS / Debian 12 | Ubuntu 22.04 |
| 域名 | 一个已解析到服务器 IP 的域名 | blog.example.com |
| 端口 | 80 / 443 对外开放 | 同左 |

## 2. 装 Docker + Compose

```bash
# 安装 Docker Engine（官方脚本）
curl -fsSL https://get.docker.com | bash

# 把当前用户加入 docker 组（免 sudo）
sudo usermod -aG docker $USER
newgrp docker

# 验证
docker --version
docker compose version
```

## 3. 克隆代码 + 配置

```bash
git clone https://github.com/<your-name>/flask-blog.git
cd flask-blog
```

### 3.1 配置 .env

```bash
cat > .env <<'EOF'
# 必改：随机生成（openssl rand -hex 32）
SECRET_KEY=换成随机字符串
JWT_SECRET_KEY=换成另一个随机字符串

# GitHub OAuth（可选，不配则登录页不显示 GitHub 按钮）
GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=

# Sentry（可选，不配则不报错上报）
SENTRY_DSN=
SENTRY_ENVIRONMENT=production

# CORS 改成你的域名
CORS_ORIGINS=https://blog.example.com
EOF
```

生成随机密钥：

```bash
openssl rand -hex 32   # 跑两次，分别填 SECRET_KEY 和 JWT_SECRET_KEY
```

## 4. 启动全部服务

```bash
# 构建并后台启动（首次约 3-5 分钟）
docker compose up -d --build

# 看状态（全部 healthy 即就绪）
docker compose ps

# 看 backend 日志确认迁移完成
docker compose logs -f backend
```

启动后访问：
- 博客前台：`http://服务器IP:8080`
- Swagger 文档：`http://服务器IP:8000/swagger`
- Grafana 面板：`http://服务器IP:3000`（admin/admin）

> 生产环境不应直接暴露 8080/8000/3000 端口，下一步用 Nginx + HTTPS 反代。

## 5. HTTPS（Let's Encrypt）

用 certbot 申请免费证书，Nginx 反代：

```bash
sudo apt install -y nginx certbot python3-certbot-nginx

# 申请证书（自动改 Nginx 配置加 HTTPS）
sudo certbot --nginx -d blog.example.com
```

Nginx 配置（`/etc/nginx/sites-available/blog`）：

```nginx
server {
    listen 80;
    server_name blog.example.com;

    # 前端静态 + /api 反代到 backend:8000
    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket（SocketIO）需要 Upgrade 头
    location /socket.io/ {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

启用并重载：

```bash
sudo ln -s /etc/nginx/sites-available/blog /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

certbot 会自动配好 443 和证书自动续期。

## 6. 备份策略

### 数据库自动备份

```bash
# 每天凌晨 3 点备份 MySQL（保留 14 天）
crontab -e
```

加一行：

```cron
0 3 * * * cd /opt/flask-blog && docker exec flaskblog-db mysqldump -uroot -proot flask_blog > backups/flask_blog_$(date +\%Y\%m\%d).sql && find backups/ -mtime +14 -delete
```

项目已自带 `scripts/backup_mysql.ps1` 和 `scripts/restore_mysql.ps1`（Windows 本地演练用），Linux 上直接用上面的 crontab 即可。

### Redis / 上传文件

- Redis 开了 AOF 持久化（`redis_data` 卷），重启不丢缓存/限流计数
- 如有用户上传文件，挂卷到 `./uploads` 并定期 rsync 到对象存储

## 7. 常用运维命令

```bash
# 看日志
docker compose logs -f backend        # 后端
docker compose logs -f worker         # Celery 异步任务

# 重启某个服务
docker compose restart backend

# 部署新版本
git pull && docker compose up -d --build backend

# 进容器排查
docker compose exec backend bash

# 数据库迁移（改了 models.py 后）
docker compose exec backend flask --app wsgi db upgrade

# 看资源占用
docker stats
```

## 8. 故障排查

| 现象 | 排查 |
|---|---|
| 前端 502 | `docker compose ps` 看 backend 是否 healthy；`docker compose logs backend` |
| 登录失败 | 看 Redis 是否起来；MySQL 是否就绪；`.env` 密钥是否改了 |
| 评论不实时推送 | 确认 `SOCKETIO_MESSAGE_QUEUE` 已配（compose 里默认配了 redis:6379/3） |
| /metrics 无数据 | `METRICS_ENABLED` 默认 true，看 backend 是否在跑 |
| 磁盘满 | `docker system df` 看镜像/卷占用；日志已配 10m×3 轮转 |

## 9. 安全清单

- [ ] `.env` 里 `SECRET_KEY` / `JWT_SECRET_KEY` 已改随机值
- [ ] 不暴露 8080/8000/3000 到公网（只开 80/443）
- [ ] 服务器防火墙（ufw）只开 22/80/443
- [ ] MySQL root 不映射 3306 到公网（compose 里只映射了 3307 给本地调试）
- [ ] `pip-audit` / `npm audit` / Trivy CI 门禁已过
- [ ] Sentry DSN 已配，异常能收到通知
