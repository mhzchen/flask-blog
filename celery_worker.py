"""Celery Worker / Beat 入口。

用法：
    celery -A celery_worker.celery worker --loglevel=info
    celery -A celery_worker.celery beat  --loglevel=info

先创建 Flask 应用并绑定 Celery，这样任务里能拿到应用上下文。
"""
from app import create_app
from app.celery_app import init_celery

flask_app = create_app()
init_celery(flask_app)

# 暴露给 celery -A 使用的实例
celery = flask_app.extensions['celery']