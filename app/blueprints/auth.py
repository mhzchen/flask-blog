from flask import Blueprint, render_template, redirect, url_for, request, flash

from flask_login import login_user, logout_user, login_required, current_user
from app.forms import RegisterForm, LoginForm
from app.models import User, db

auth_bp = Blueprint('auth', __name__)


@auth_bp.route("/register", methods=['GET', 'POST'])
def register():
    """用户注册（使用 Flask-WTF 表单）"""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    form = RegisterForm()

    # form.validate_on_submit() 在 POST 请求时校验表单，GET 或校验失败返回 False
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        flash(f'注册成功，欢迎你，{user.username}！', 'success')
        return redirect(url_for('main.index'))

    return render_template('register.html', form=form)


@auth_bp.route("/login", methods=['GET', 'POST'])
def login():
    """用户登录（使用 Flask-WTF 表单）"""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    form = LoginForm()

    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('用户名或密码错误。', 'error')
            return render_template('login.html', form=form)

        login_user(user, remember=form.remember.data)
        flash(f'欢迎回来，{user.username}！', 'success')
        next_page = request.args.get('next')
        return redirect(next_page or url_for('main.index'))

    return render_template('login.html', form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    """用户登出"""
    logout_user()
    flash('已安全登出。', 'info')
    return redirect(url_for('main.index'))
