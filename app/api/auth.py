import time

from flask import Blueprint, current_app, g, jsonify
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_jwt,
    get_jwt_identity,
    jwt_required,
)

from app import limiter
from app.jwt_blacklist import revoke_token, revoke_user
from app.schemas import LoginBody, PasswordChangeBody, RegisterBody, validate_body
from app.services import ServiceError, auth_service
from app.tasks import enqueue, send_welcome_email

auth_bp = Blueprint("auth", __name__)


@auth_bp.post("/register")
@limiter.limit("5 per minute")
@validate_body(RegisterBody)
def register():
    """用户注册。

    请求体经 Pydantic 校验（用户名/邮箱/密码长度、邮箱格式），
    校验通过后创建用户、返回 token，并异步发送欢迎邮件。
    """
    body = g.validated
    try:
        user = auth_service.register(body.username.strip(), body.email, body.password)
    except ServiceError as e:
        return jsonify({"error": e.message}), e.status_code

    # 异步发送欢迎邮件（broker 不可用时不影响注册）
    enqueue(send_welcome_email, user.id)

    access_token = create_access_token(identity=str(user.id))
    refresh_token = create_refresh_token(identity=str(user.id))
    return jsonify({
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": user.to_dict(),
    }), 201


@auth_bp.post("/login")
@limiter.limit("10 per minute")
@validate_body(LoginBody)
def login():
    """用户登录：用户名 + 密码，成功返回 token。"""
    body = g.validated
    try:
        user = auth_service.login(body.username.strip(), body.password)
    except ServiceError as e:
        # 账号锁定等业务校验失败（429），直接返回，不进入 401 分支
        return jsonify({"error": e.message}), e.status_code
    if user is None:
        return jsonify({"error": "用户名或密码错误。"}), 401

    access_token = create_access_token(identity=str(user.id))
    refresh_token = create_refresh_token(identity=str(user.id))
    return jsonify({
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": user.to_dict(),
    })


@auth_bp.get("/me")
@jwt_required()
def me():
    """返回当前登录用户信息"""
    try:
        user = auth_service.get_or_404(int(get_jwt_identity()))
    except ServiceError as e:
        return jsonify({"error": e.message}), e.status_code
    return jsonify({"user": user.to_dict()})


@auth_bp.post("/refresh")
@limiter.limit("30 per minute")
@jwt_required(refresh=True)
def refresh():
    """用 refresh token 换取新的 access token（access 过期后自动续期，无需重新登录）。

    refresh token 有效期较长（默认 7 天），仅用于换 access，不直接访问业务接口。
    """
    try:
        user = auth_service.get_or_404(int(get_jwt_identity()))
    except ServiceError as e:
        return jsonify({"error": e.message}), e.status_code
    new_access = create_access_token(identity=str(user.id))
    return jsonify({"access_token": new_access})


@auth_bp.post("/logout")
@jwt_required()
def logout():
    """登出：把当前 access token 的 jti 加入黑名单，之后该 token 立即失效。

    Redis 不可用时降级为"到期自然失效"（仍返回成功，不报错）。
    """
    payload = get_jwt()
    ttl = max(int(payload.get('exp', time.time())) - int(time.time()), 1)
    ok = revoke_token(current_app._get_current_object(), payload.get('jti'), ttl)
    return jsonify({"message": "已注销。" if ok else "已注销（黑名单暂不可用，token 到期前仍有效）。"})


@auth_bp.post("/password")
@jwt_required()
@validate_body(PasswordChangeBody)
def change_password():
    """修改密码：校验旧密码后更新，并使该用户所有旧 token（含 refresh）立即失效，需重新登录。"""
    body = g.validated
    uid = int(get_jwt_identity())
    try:
        auth_service.change_password(uid, body.old_password, body.new_password)
    except ServiceError as e:
        return jsonify({"error": e.message}), e.status_code
    revoke_user(current_app._get_current_object(), uid)
    return jsonify({"message": "密码已更新，请重新登录。"})
