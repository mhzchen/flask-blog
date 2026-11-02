# 后端镜像：Flask + gunicorn（非 root 运行，最小权限）
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# 建非 root 运行用户（uid/gid 1000，与宿主机普通用户对齐，便于后续挂载卷）
RUN groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid appuser --create-home --shell /usr/sbin/nologin appuser

WORKDIR /app

# 先装依赖，利用 Docker 层缓存
COPY requirements.txt .
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

# 拷贝应用代码（.dockerignore 已排除 venv/.env/logs/tests/scripts 等）
COPY . .

RUN chmod +x docker_entrypoint.sh \
    && chown -R appuser:appuser /app

# 以非 root 运行：容器被攻破也无法获得 root 权限（纵深防御）
USER appuser

EXPOSE 8000

# 入口脚本：等待 DB -> 首次建表/seed -> 启动 gunicorn
CMD ["./docker_entrypoint.sh"]