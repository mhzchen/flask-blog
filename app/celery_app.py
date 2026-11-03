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
        # 任务执行超时保护：硬超时 60s 杀掉，软超时 50s 告警，避免任务 hang 占用 worker
        task_time_limit=60,
        task_soft_time_limit=50,
        # Redis/broker 不可用时快速失败（避免每个请求被连接重试阻塞数十秒）
        broker_connection_retry=False,
        broker_connection_retry_on_startup=False,
        broker_connection_max_retries=0,
        broker_transport_options={'socket_connect_timeout': 2, 'socket_timeout': 2},
        task_publish_retry=False,
        # 测试环境可开启 eager：.delay() 同步执行，不发到 broker
        task_always_eager=app.config.get('CELERY_TASK_ALWAYS_EAGER', False),
        task_eager_propagates=app.config.get('CELERY_TASK_EAGER_PROPAGATES', False),
        include=['app.tasks'],
    )

    # 定时任务（Celery Beat 使用）：
    # - heartbeat-every-minute   每分钟心跳（保活探测）
    # - warm-hot-cache-2min      每 2 分钟预热热点缓存（首页列表/热门详情），防冷启动打穿 DB
    # - prune-deadletter-hourly  每小时清理死信列表，只保留最近 DEADLETTER_MAX 条
    celery.conf.beat_schedule = {
        'heartbeat-every-minute': {
            'task': 'tasks.periodic_ping',
            'schedule': 60.0,
        },
        'warm-hot-cache-2min': {
            'task': 'tasks.warm_hot_cache',
            'schedule': 120.0,
        },
        'prune-deadletter-hourly': {
            'task': 'tasks.prune_deadletter',
            'schedule': 3600.0,
        },
    }

    # 队列隔离：维护类/关键任务路由到 critical 队列，由独立 worker-critical 独占消费；
    # 其余业务任务默认走 default 队列。以此实现关键任务优先的优先级隔离。
    celery.conf.task_routes = {
        'tasks.warm_hot_cache': {'queue': 'critical'},
        'tasks.prune_deadletter': {'queue': 'critical'},
    }

    # 任务失败告警目标（webhook URL）：空则不推送（测试环境关闭）
    celery.conf['alert_webhook_url'] = app.config.get('ALERT_WEBHOOK_URL', '')

    app.extensions['celery'] = celery

    _register_failure_webhook(celery)

    # 让每个任务在 Flask 应用上下文里执行，任务里才能用 db / current_app
    class ContextTask(celery.Task):
        abstract = True

        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery


def _register_failure_webhook(celery):
    """任务失败时推送告警到 webhook（幂等注册，重复调用不重复注册）。

    失败信息：task 名称 / task_id / 异常摘要 / 参数。推送失败绝不抛错，
    因为告警通道故障不能反过来影响任务执行/worker 存活。
    """
    from celery.signals import task_failure

    if getattr(_register_failure_webhook, '_registered', False):
        return
    _register_failure_webhook._registered = True

    @task_failure.connect
    def _on_task_failure(sender=None, task_id=None, args=None, kwargs=None, einfo=None, **kw):
        url = (celery.conf.get('alert_webhook_url') or '').strip()
        if not url:
            return
        name = getattr(sender, 'name', None) or 'unknown'
        payload = {
            'type': 'celery_task_failure',
            'task': name,
            'task_id': task_id,
            'args': list(args or []),
            'kwargs': dict(kwargs or {}),
            'error': ((einfo and str(einfo.exception)) or '') if einfo is not None else '',
        }
        import json
        import urllib.request
        try:
            body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
            req = urllib.request.Request(
                url, data=body, headers={'Content-Type': 'application/json'}, method='POST')
            with urllib.request.urlopen(req, timeout=3):
                pass
        except Exception:
            # 告警推送失败不能影响 worker/任务本身
            pass
