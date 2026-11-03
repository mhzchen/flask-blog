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
