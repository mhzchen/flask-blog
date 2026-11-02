"""安全纵深：统一安全响应头 + 同源检查。

设计原则：
- 用 after_request 给每个响应注入浏览器安全头，防点击劫持 / MIME 嗅探 / 内容注入；
- CSP 用白名单收紧可加载来源，降低 XSS 影响面；
- 通过 app.config["SECURITY_HEADERS_ENABLED"] 控制开关（测试环境可关）。
"""
from flask import request

# 默认安全头（生产生效）
_DEFAULT_HEADERS = {
    # 内容安全策略：只允许本站与后端 API 来源，禁止内联脚本/远程 iframe，缓解 XSS
    "Content-Security-Policy": "default-src 'self'; "
                               "script-src 'self'; "
                               "style-src 'self' 'unsafe-inline'; "
                               "img-src 'self' data:; "
                               "font-src 'self'; "
                               "frame-ancestors 'none'; "
                               "object-src 'none'; "
                               "base-uri 'self'",
    # 禁止被 iframe 嵌入，防点击劫持（frame-ancestors 与它双保险）
    "X-Frame-Options": "DENY",
    # 禁止 MIME 类型嗅探，防 Content-Type 被浏览器猜错
    "X-Content-Type-Options": "nosniff",
    # 禁止浏览器启动 XSS 过滤器的自动行为（避免绕过既有转义）
    "X-XSS-Protection": "0",
    # 只在 HTTPS 下才允许引用本页（生产若走 TLS，防 Referer 泄露）
    "Referrer-Policy": "strict-origin-when-cross-origin",
    # HTTP 严格传输安全：仅当本请求来自 HTTPS 时才下发，避免明文环境被误加
    # (由 _add_headers 动态判断，这里不写死)
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
}


def register_security_headers(app):
    """注册安全响应头中间件。"""

    @app.after_request
    def _add_headers(resp):
        if not app.config.get("SECURITY_HEADERS_ENABLED", True):
            return resp
        for k, v in _DEFAULT_HEADERS.items():
            resp.headers.setdefault(k, v)
        # HSTS 只在 HTTPS 下下发；本地 HTTP 开发不下发，避免浏览器缓存错误策略
        if request.scheme == "https":
            resp.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )
        return resp
