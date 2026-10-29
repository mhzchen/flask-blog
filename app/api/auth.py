from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity

from app.models import User, db
from app.tasks import enqueue, send_welcome_email

auth_bp = Blueprint('auth', __name__)


@auth_bp.post('/register')
def register():
    """用户注册，成功后直接返回 token，并异步发送欢迎邮件"""
    data = request.get_json(silent=True) or {}
    username = (data.get('username') or '').strip()
    email = (data.get('email') or '').strip()
    password = data.get('password') or ''

    # 校验必填字段
    if not username or not email or not password:
        return jsonify({'error': '所有字段都必须填写。'}), 400
    if len(password) < 6:
        return jsonify({'error': '密码至少 6 位。'}), 400

    # 检查用户名和邮箱是否已存在
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
def login():
    """用户登录，成功返回 token"""
    data = request.get_json(silent=True) or {}
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''

    user = User.query.filter_by(username=username).first()
    if user is None or not user.check_password(password):
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