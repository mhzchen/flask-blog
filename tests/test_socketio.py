# -*- coding: utf-8 -*-
"""#54 WebSocket 广播函数测试。"""
from app.socketio import emit_comment_new, emit_post_new, socketio


def _capture_emit(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        socketio, 'emit',
        lambda event, data, namespace='/': captured.update(event=event, data=data, namespace=namespace))
    return captured


def test_emit_comment_new_broadcasts_event(monkeypatch):
    captured = _capture_emit(monkeypatch)
    comment = {'id': 1, 'content': 'hi', 'author': 'alice'}
    emit_comment_new(comment)
    assert captured['event'] == 'comment:new'
    assert captured['data'] == comment
    assert captured['namespace'] == '/'


def test_emit_post_new_broadcasts_event(monkeypatch):
    captured = _capture_emit(monkeypatch)
    post = {'id': 9, 'title': 'New Post'}
    emit_post_new(post)
    assert captured['event'] == 'post:new'
    assert captured['data'] == post
    assert captured['namespace'] == '/'


# ---------- #57 生产化：make_client_manager（跨进程广播 redis 消息队列） ----------


def test_make_client_manager_none_when_no_queue():
    """未配置 SOCKETIO_MESSAGE_QUEUE -> 单进程降级，返回 None。"""
    from app.socketio import make_client_manager
    from flask import Flask

    app = Flask(__name__)
    app.config['SOCKETIO_MESSAGE_QUEUE'] = ''
    assert make_client_manager(app) is None


def test_make_client_manager_redis_manager_when_queue():
    """配置了 SOCKETIO_MESSAGE_QUEUE -> 返回 RedisManager（redis pub/sub 跨进程广播）。"""
    from app.socketio import make_client_manager
    from flask import Flask

    from socketio import RedisManager

    app = Flask(__name__)
    app.config['SOCKETIO_MESSAGE_QUEUE'] = 'redis://localhost:6379/3'
    cm = make_client_manager(app)
    assert isinstance(cm, RedisManager)
