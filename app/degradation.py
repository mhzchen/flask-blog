"""统一服务降级开关与观测（#58）。

背景：项目里 Redis 缓存/登录锁定/幂等/JWT 黑名单、Meilisearch、Celery broker、
DB 读写分离等各自都有 try/except 降级，但分散、无法统一配置、不可观测。
本模块把"服务降级"收口为可配置、可观测的横切设施：

  - 总开关 SERVICE_DEGRADATION_ENABLED（默认 true=依赖故障时降级继续服务；
    false=遇故障 fail-fast 抛错，不吞错误）；
  - 每服务开关 DEGRADATION_<SERVICE>（redis_cache / redis_login / redis_jwt /
    redis_idem / meilisearch / celery / otel / dbrouting，默认 true，可单独关闭）；
  - degrade(service, reason)：记录一次降级（计数 + 结构化 WARNING 日志 + 状态标记），绝不抛错；
  - is_degraded / degradation_summary()：查询各服务当前降级状态（供 /system/degradations
    与 metrics 观测）。

接入点把原有"静默 except 降级"换成调用 degrade() 即可，行为不变但可获得降级事件日志与汇总。
"""
import logging
import threading
from datetime import datetime

_logger = logging.getLogger('app.degradation')
_lock = threading.Lock()

SERVICES = (
    'redis_cache', 'redis_login', 'redis_jwt', 'redis_idem', 'redis_ratelimit',
    'meilisearch', 'celery', 'otel', 'dbrouting',
)

# service -> {'enabled': bool, 'count': int, 'last_reason': str, 'last_ts': str, 'degraded': bool}
_state: dict[str, dict] = {}


def _service_on(app, service):
    """该服务是否允许降级（总开关 && 该服务开关）；false -> fail-fast，不降级。"""
    try:
        if not app.config.get('SERVICE_DEGRADATION_ENABLED', True):
            return False
        return bool(app.config.get('DEGRADATION_%s' % service.upper(), True))
    except Exception:
        return True


def degrade(service, reason, app=None):
    """记录一次服务降级事件；返回 True。任何异常都不外抛。

    无 Flask 应用上下文（如纯函数/任务无上下文场景）时按开关默认值记录，不因此丢弃事件。
    """
    if service not in SERVICES:
        return True
    try:
        if app is None:
            try:
                from flask import current_app
                app = current_app._get_current_object()  # type: ignore[attr-defined]
            except Exception:
                app = None
        enabled = _service_on(app, service) if app is not None else True
        with _lock:
            st = _state.setdefault(service, {
                'enabled': enabled, 'count': 0, 'last_reason': '', 'last_ts': '', 'degraded': False,
            })
            st['enabled'] = enabled
            st['count'] += 1
            st['last_reason'] = str(reason)[:200]
            st['last_ts'] = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
            st['degraded'] = True
        _logger.warning('degradation', extra={'service': service, 'reason': str(reason)[:200]})
    except Exception:
        pass
    return True


def is_degraded(service):
    """查询某服务当前是否处于降级状态。"""
    with _lock:
        st = _state.get(service)
        return bool(st and st['degraded'])


def degradation_summary():
    """返回各服务降级状态汇总（服务名/开关/累计次数/最近原因/时间/是否降级）。"""
    with _lock:
        return [
            {
                'service': s,
                'enabled': st['enabled'],
                'count': st['count'],
                'last_reason': st['last_reason'],
                'last_ts': st['last_ts'],
                'degraded': st['degraded'],
            }
            for s, st in sorted(_state.items())
        ]
