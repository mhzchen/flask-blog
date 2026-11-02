"""HTML 净化工具（XSS 防护）。

文章内容支持富文本（HTML），但直接存原样会有存储型 XSS 风险
（<script>、<img onerror=...>、javascript: 协议等可在前端 v-html 时执行）。
这里用 bleach 白名单净化：只保留安全的标签和属性，剔除一切脚本向量。

设计要点：
- 白名单标签：常用富文本标签，不含 <script>/<style>/<iframe>/<object> 等危险标签；
- 白名单属性：仅 href/src/title/alt 等，剔除所有 on* 事件属性；
- 链接协议：href 仅允许 http/https/mailto，剔除 javascript:/data: 等；
- 过滤 style：避免 CSS 注入（expression/behavior 等老式向量）。
"""
import bleach

# 允许的富文本标签
ALLOWED_TAGS = [
    'a', 'abbr', 'acronym', 'b', 'blockquote', 'br', 'code', 'em',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'hr', 'i', 'img', 'li', 'ol',
    'p', 'pre', 'strong', 'sub', 'sup', 'table', 'tbody', 'td', 'th',
    'thead', 'tr', 'ul', 'span',
]

# 允许的属性（不含 on* 事件属性、不含 style）
ALLOWED_ATTRIBUTES = {
    'a': ['href', 'title', 'target', 'rel'],
    'img': ['src', 'alt', 'title', 'width', 'height'],
    '*': ['class', 'id'],
}

# 允许的链接协议
ALLOWED_PROTOCOLS = ['http', 'https', 'mailto']


def sanitize_html(content):
    """净化 HTML，剔除脚本/XSS 向量，返回安全的 HTML 字符串。"""
    if not content:
        return content or ''
    return bleach.clean(
        content,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
    )