"""Celery 实例与 Flask 集成。

架构说明：
- Web 进程：create_app() 里调用 init_celery(app)，把 Celery 绑定到应用上下文；
- Worker/Beat 进程：通过 celery_worker.py 入口创建应用并绑定，避免循环导入。
这样任务里可以直接使用 db.session / current_app。
"""
from celery import Celery

# 全局 Celery 实例。include 让 worker 能自动发现并注册 app.tasks 里的任务。
celery = Celery('flask-blog', include=['app.tasks'])


def init_celery(app):
    """用 Flask 应用配置初始化 Celery，并把任务绑定到该应用上下文。"""
    celery.conf.update(
        broker_url=app.config.get('CELERY_BROKER_URL', 'redis://localhost:6379/1'),
        result_backend=app.config.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/1'),
        task_serializer='json',
        result_serializer='json',
        accept_content=['json'],
        timezone='Asia/Shanghai',
        enable_utc=True,
        task_track_started=True,
        # 测试环境可开启 eager：.delay() 同步执行，不发到 broker
        task_always_eager=app.config.get('CELERY_TASK_ALWAYS_EAGER', False),
        task_eager_propagates=app.config.get('CELERY_TASK_EAGER_PROPAGATES', False),
        include=['app.tasks'],
    )

    # 定时任务（Celery Beat 使用）：每分钟心跳，演示周期调度
    celery.conf.beat_schedule = {
        'heartbeat-every-minute': {
            'task': 'tasks.periodic_ping',
            'schedule': 60.0,
        },
    }

    app.extensions['celery'] = celery

    # 让每个任务在 Flask 应用上下文里执行，任务里才能用 db / current_app
    class ContextTask(celery.Task):
        abstract = True

        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery