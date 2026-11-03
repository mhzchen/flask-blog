# -*- coding: utf-8 -*-
"""WebSocket 实时推送（Flask-SocketIO）——生产化。

- 单进程（开发 / 单 worker）：async_mode='threading'，socketio.run(app) 同时提供 HTTP + WS。
- 多 worker / 多实例：必须配 SOCKETIO_MESSAGE_QUEUE（redis 消息队列），Flask-SocketIO
  经 redis pub/sub 让广播跨进程生效；配了 message queue 时用 RedisManager（threading
  同步 Server 对应的同步管理器）。未配则广播只在本进程内。
"""
from flask_socketio import SocketIO

socketio = SocketIO(async_mode='threading')


def make_client_manager(app):
    """按配置构造跨进程广播用的 redis 消息队列 manager；未配置返回 None（单进程降级）。"""
    url = app.config.get('SOCKETIO_MESSAGE_QUEUE')
    if not url:
        return None
    from socketio import RedisManager
    return RedisManager(url)


def register_socket_events():
    """注册基础连接事件（connect/disconnect）。鉴权如需校验在此扩展。"""

    @socketio.on('connect')
    def on_connect():
        # 匿名可连接（只读广播）；如需登录鉴权，可在握手时校验 auth token
        pass

    @socketio.on('disconnect')
    def on_disconnect():
        pass


def emit_comment_new(comment_dict):
    """广播新评论事件给所有在线客户端。"""
    socketio.emit('comment:new', comment_dict, namespace='/')


def emit_post_new(post_dict):
    """广播新文章事件给所有在线客户端。"""
    socketio.emit('post:new', post_dict, namespace='/')
