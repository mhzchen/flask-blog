"""JWT 注销/黑名单：登出即时吊销 token，改密使该用户旧 token 全部失效。

存储复用缓存 Redis（可降级：Redis 不可用/未配置时放行，绝不因黑名单检查拖垮认证）。
key 设计：
  jwt_blacklist:<jti>   —— 已登出的单个 token（TTL = token 剩余有效期，到期自动清理）
  jwt_revoke_user:<uid> —— 用户级撤销时间戳（改密/强制下线用，早于此时间的签发全部失效）
"""
import time

from app.cache import _client
from app.degradation import degrade

_BLACKLIST_PREFIX = "jwt_blacklist"
_REVOKE_PREFIX = "jwt_revoke_user"


def revoke_token(app, jti, remaining_ttl):
    """登出：把指定 token 的 jti 加入黑名单（TTL = 剩余有效期，自动过期）。"""
    client = _client(app)
    if client is None:
        return False
    try:
        if remaining_ttl > 0:
            client.setex(f"{_BLACKLIST_PREFIX}:{jti}", remaining_ttl, "1")
        else:
            client.set(f"{_BLACKLIST_PREFIX}:{jti}", "1")
        return True
    except Exception as e:
        degrade('redis_jwt', 'revoke_token redis down: %s' % e, app)
        return False


def revoke_user(app, uid):
    """改密/强制下线：写入撤销时间戳，该用户所有更早签发的 token 立即失效。"""
    client = _client(app)
    if client is None:
        return False
    try:
        client.set(f"{_REVOKE_PREFIX}:{uid}", int(time.time()))
        return True
    except Exception as e:
        degrade('redis_jwt', 'revoke_user redis down: %s' % e, app)
        return False


def is_blocked(app, jti, uid, iat):
    """检查 token 是否被吊销：jti 在黑名单，或用户撤销时间晚于 token 签发时间。

    Redis 不可用/未配置时降级返回 False（放行），保证认证不因黑名单服务故障而中断。
    """
    client = _client(app)
    if client is None:
        return False
    try:
        if client.get(f"{_BLACKLIST_PREFIX}:{jti}"):
            return True
        if uid is not None:
            rev = client.get(f"{_REVOKE_PREFIX}:{uid}")
            if rev and int(rev) > int(iat or 0):
                return True
        return False
    except Exception as e:
        degrade('redis_jwt', 'is_blocked redis down -> allow: %s' % e, app)
        return False
