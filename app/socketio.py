# -*- coding: utf-8 -*-
"""WebSocket 实时推送（Flask-SocketIO）。

- 开发：async_mode='threading'，socketio.run(app) 同时提供 HTTP + WebSocket。
- 生产：需 ASGI server（hypercorn）挂载本 socketio 应用；多 worker / 多实例广播
  必须配置 redis message queue 适配器（SocketIO.AsyncRedisManager），否则广播不跨进程。

用法：
    评论/文章发布时调用 emit_comment_new / emit_post_new 广播事件，
    前端 socket.io-client 订阅 'comment:new' / 'post:new' 实时展示。
"""
from flask_socketio import SocketIO

socketio = SocketIO(async_mode='threading')


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
