# 后端镜像：Flask + gunicorn
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# 先装依赖，利用 Docker 层缓存
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 拷贝应用代码（.dockerignore 已排除 venv/.env/logs 等）
COPY . .

RUN chmod +x docker_entrypoint.sh

EXPOSE 8000

# 入口脚本：等待 DB -> 首次建表/seed -> 启动 gunicorn
CMD ["./docker_entrypoint.sh"]