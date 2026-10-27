from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from config import Config

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()


def create_app(config_class=Config):
    """应用工厂：根据配置类创建 Flask 应用实例"""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # 初始化扩展（先创建 app 实例，再将扩展绑定到 app）
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)

    login_manager.login_view = 'auth.login'
    login_manager.login_message = '请先登录后再访问。'

    # 注册 Flask-Admin 后台管理
    from flask_admin import Admin
    from flask_admin.contrib.sqla import ModelView
    from app.models import Post, Category, User

    class PostAdmin(ModelView):
        column_list = ['title', 'category', 'created_at', 'updated_at']
        column_searchable_list = ['title', 'summary']
        column_filters = ['category', 'created_at']
        form_columns = ['title', 'slug', 'summary', 'content', 'category']

    class CategoryAdmin(ModelView):
        column_list = ['name', 'slug']
        form_columns = ['name', 'slug']

    admin = Admin(app, name='RUNOOB 博客后台')
    admin.add_view(PostAdmin(Post, db.session, name='文章'))
    admin.add_view(CategoryAdmin(Category, db.session, name='分类'))
    admin.add_view(ModelView(User, db.session, name='用户'))

    # 注册 Blueprint（在 create_app 内部导入，避免循环导入）
    from app.blueprints.main import main_bp
    from app.blueprints.posts import posts_bp
    from app.blueprints.auth import auth_bp
    from app.blueprints.user import user_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(posts_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(user_bp)

    # user_loader 需要在 app 存在后定义
    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    return app
