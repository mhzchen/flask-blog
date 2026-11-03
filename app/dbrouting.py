"""SQLAlchemy 读写分离：读走从库、写走主库（RoutingSession）。

Flask-SQLAlchemy 3.x 官方推荐的 session 路由写法：自定义 Session.get_bind，
flush/commit（写）固定走 default 主库引擎；普通查询（读）在配置了 slave bind 时走从库。
未配置 slave（dev/SQLite/测试）时所有查询回落到 default，行为与原来完全一致。
"""
from flask import current_app
from flask_sqlalchemy.session import Session as FASession


class RoutingSession(FASession):
    """读写分离 session：写(default 主库) / 读(slave 从库，有则用)。"""

    def get_bind(self, mapper=None, clause=None, bind=None, **kw):
        engines = current_app.extensions['sqlalchemy'].engines
        if self._flushing:
            return engines[None]  # 写操作走 default 主库（None key = 默认引擎）
        if 'slave' in engines:
            return engines['slave']  # 读操作有从库则走从库
        return engines[None]
