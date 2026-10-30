"""统一 JSON 错误响应 + 全局异常处理。

目标：不管错误来自哪里（404/405/abort/未捕获异常），
都返回统一结构的 JSON，而不是 Flask 默认的 HTML 错误页。
"""
from flask import jsonify
from werkzeug.exceptions import HTTPException


def register_error_handlers(app):
    """注册全局错误处理器。"""

    @app.errorhandler(HTTPException)
    def handle_http_exception(e):
        """处理所有 HTTPException（404/405/400/abort 等）。"""
        return jsonify({
            'error': e.description if e.description else e.name,
            'code': e.code,
        }), e.code

    @app.errorhandler(Exception)
    def handle_unhandled(e):
        """兜底：未捕获异常统一返回 500 JSON。"""
        app.logger.exception('未处理异常: %s', e)
        if app.debug:
            # 开发环境暴露细节方便排查
            return jsonify({'error': '服务器内部错误', 'code': 500, 'detail': str(e)}), 500
        # 生产环境不泄露堆栈；code 与 HTTPException 分支一致，前端可统一判断
        return jsonify({'error': '服务器内部错误', 'code': 500}), 500