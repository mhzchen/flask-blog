from flask import Blueprint, request, jsonify, g
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity

from app.models import User, db
from app.tasks import enqueue, send_welcome_email
from app.schemas import RegisterBody, LoginBody, validate_body

auth_bp = Blueprint('auth', __name__)


@auth_bp.post('/register')
@validate_body(RegisterBody)
def register():
    """用户注册。

    请求体经 Pydantic 校验（用户名/邮箱/密码长度、邮箱格式），
    校验通过后创建用户、返回 token，并异步发送欢迎邮件。
    """
    body = g.validated
    username = body.username.strip()
    email = body.email
    password = body.password

    # 业务校验：用户名/邮箱是否已存在
    if User.query.filter_by(username=username).first():
        return jsonify({'error': '用户名已被使用。'}), 409
    if User.query.filter_by(email=email).first():
        return jsonify({'error': '邮箱已被注册。'}), 409

    user = User(username=username, email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    # 异步发送欢迎邮件（broker 不可用时不影响注册）
    enqueue(send_welcome_email, user.id)

    token = create_access_token(identity=str(user.id))
    return jsonify({'access_token': token, 'user': user.to_dict()}), 201


@auth_bp.post('/login')
@validate_body(LoginBody)
def login():
    """用户登录：用户名 + 密码，成功返回 token。"""
    body = g.validated
    user = User.query.filter_by(username=body.username.strip()).first()
    if user is None or not user.check_password(body.password):
        return jsonify({'error': '用户名或密码错误。'}), 401

    token = create_access_token(identity=str(user.id))
    return jsonify({'access_token': token, 'user': user.to_dict()})


@auth_bp.get('/me')
@jwt_required()
def me():
    """返回当前登录用户信息"""
    user = db.session.get(User, int(get_jwt_identity()))
    if user is None:
        return jsonify({'error': '用户不存在。'}), 404
    return jsonify({'user': user.to_dict()})