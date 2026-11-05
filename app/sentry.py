"""Sentry 错误追踪：未捕获异常自动上报，带 request / 用户上下文。

与 OpenTelemetry 互补：OTel 管链路追踪（慢请求、跨服务调用链），
Sentry 管异常聚合、堆栈、release 告警。DSN 未配置时完全跳过，
开发/测试不发任何网络请求，也不影响业务。
"""
import logging

import sentry_sdk
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.flask import FlaskIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

_logger = logging.getLogger("app.sentry")
_initialized = False


def init_sentry(app):
    """按 SENTRY_DSN 配置初始化 Sentry；未配置或已初始化则跳过（幂等）。"""
    global _initialized
    if _initialized:
        return
    dsn = app.config.get("SENTRY_DSN", "")
    if not dsn:
        _logger.info("Sentry 未配置 DSN，跳过初始化")
        return
    _initialized = True
    sentry_sdk.init(
        dsn=dsn,
        environment=app.config.get("SENTRY_ENVIRONMENT", "development"),
        release=app.config.get("SENTRY_RELEASE", "") or None,
        traces_sample_rate=float(app.config.get("SENTRY_TRACES_SAMPLE_RATE", 0.1)),
        send_default_pii=False,  # 不上报 IP / Cookie 等敏感信息
        integrations=[FlaskIntegration(), CeleryIntegration(), SqlalchemyIntegration()],
        debug=False,
    )
    _logger.info("Sentry 已初始化 env=%s", app.config.get("SENTRY_ENVIRONMENT"))
