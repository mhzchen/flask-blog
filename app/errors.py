# -*- coding: utf-8 -*-
"""统一 JSON 错误响应：error envelope + 业务错误码枚举 + 全局异常处理。

目标：不管错误来自哪里（404/405/abort/业务异常/未捕获异常/校验失败），
都返回统一结构的 JSON envelope，并附 trace_id / path，便于前端统一判断、日志串联排查。

envelope 结构：
    { code: <HTTP 状态码>, status: <ok|error>, error_code: <业务错误码>,
      message: <人类可读>, error: <同 message，兼容旧客户端>, trace_id, path, errors? }

保留 code(HTTP) 与 error 字段以兼容历史客户端/测试；新增 error_code 供程序化判断。
"""
from enum import Enum

from flask import jsonify, request
from werkzeug.exceptions import HTTPException

from app.telemetry import _current_trace_id


class ErrorCode(str, Enum):
    """业务错误码枚举：程序化判断错误类型，不依赖 HTTP 状态码字符串。"""

    VALIDATION_ERROR = 'VALIDATION_ERROR'        # 请求参数/字段校验失败 (400/422)
    UNAUTHORIZED = 'UNAUTHORIZED'                # 未认证 (401)
    TOKEN_EXPIRED = 'TOKEN_EXPIRED'              # token 过期/无效 (401)
    FORBIDDEN = 'FORBIDDEN'                      # 无权限 (403)
    NOT_FOUND = 'NOT_FOUND'                      # 资源不存在 (404)
    METHOD_NOT_ALLOWED = 'METHOD_NOT_ALLOWED'    # 方法不允许 (405)
    CONFLICT = 'CONFLICT'                        # 冲突（已存在/状态冲突）(409)
    RATE_LIMITED = 'RATE_LIMITED'                # 触发限流 (429)
    UNSUPPORTED_VERSION = 'UNSUPPORTED_VERSION'  # 不支持的 API 版本 (410)
    INTERNAL_ERROR = 'INTERNAL_ERROR'            # 未捕获的服务器错误 (500)


# HTTP 状态码 -> 业务错误码 映射（供 HTTPException 与默认兜底使用）
_HTTP_TO_CODE = {
    400: ErrorCode.VALIDATION_ERROR,
    401: ErrorCode.UNAUTHORIZED,
    403: ErrorCode.FORBIDDEN,
    404: ErrorCode.NOT_FOUND,
    405: ErrorCode.METHOD_NOT_ALLOWED,
    409: ErrorCode.CONFLICT,
    410: ErrorCode.UNSUPPORTED_VERSION,
    422: ErrorCode.VALIDATION_ERROR,
    429: ErrorCode.RATE_LIMITED,
    500: ErrorCode.INTERNAL_ERROR,
}


class AppError(Exception):
    """业务异常：携带 HTTP 状态、业务错误码与可读消息，由全局 handler 统一转 envelope。

    用法：在服务层/路由里 `raise AppError('文章不存在', 404)`；
    handler 自动转成 {code:404, error_code:'NOT_FOUND', message:'文章不存在', ...}。
    """

    def __init__(self, message, status_code=400, error_code=None, errors=None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or _HTTP_TO_CODE.get(status_code, ErrorCode.VALIDATION_ERROR)
        self.errors = errors  # 校验类错误的字段级明细（可选）


def _envelope(message, status_code, error_code, errors=None):
    """构造统一错误 envelope。"""
    trace_id = _current_trace_id()
    code = error_code.value if isinstance(error_code, ErrorCode) else error_code
    return {
        'code': status_code,                       # HTTP 状态码（兼容旧客户端）
        'status': 'error',
        'error_code': code,                        # 业务错误码（程序化判断用）
        'message': message,
        'error': message,                          # 兼容旧响应字段
        'trace_id': trace_id or None,
        'path': request.path,
        'errors': errors,
    }


def register_error_handlers(app):
    """注册全局错误处理器：HTTPException / AppError / 未捕获异常 统一转 JSON envelope。"""

    @app.errorhandler(HTTPException)
    def handle_http_exception(e):
        """处理所有 HTTPException（404/405/400/abort 等）。"""
        code = _HTTP_TO_CODE.get(e.code, ErrorCode.INTERNAL_ERROR)
        msg = e.description if e.description else e.name
        return jsonify(_envelope(msg, e.code, code)), e.code

    @app.errorhandler(AppError)
    def handle_app_error(e):
        """处理业务异常 AppError：自动映射错误码并返回对应 HTTP 状态。"""
        return jsonify(_envelope(e.message, e.status_code, e.error_code, e.errors)), e.status_code

    @app.errorhandler(Exception)
    def handle_unhandled(e):
        """兜底：未捕获异常统一返回 500 JSON envelope。"""
        app.logger.exception('未处理异常: %s', e)
        if app.debug:
            # 开发环境暴露细节方便排查
            return jsonify(_envelope('服务器内部错误', 500, ErrorCode.INTERNAL_ERROR, str(e))), 500
        # 生产环境不泄露堆栈；code 与 HTTPException 分支一致，前端可统一判断
        return jsonify(_envelope('服务器内部错误', 500, ErrorCode.INTERNAL_ERROR)), 500
