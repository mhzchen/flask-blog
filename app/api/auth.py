from flask import Blueprint, g, jsonify
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_jwt_identity,
    jwt_required,
)

from app import limiter
from app.schemas import LoginBody, RegisterBody, validate_body
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
    user = auth_service.login(body.username.strip(), body.password)
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
