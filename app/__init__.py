from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from config import Config

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()


def create_app(config_class=Config):
    """应用工厂：根据配置类创建 Flask 应用实例"""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # 初始化扩展
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    CORS(app, resources={r"/api/*": {"origins": app.config.get("CORS_ORIGINS", "*")}})

    # 注册 API 蓝图（在 create_app 内部导入，避免循环导入）
    from app.api.auth import auth_bp
    from app.api.posts import posts_bp
    from app.api.categories import categories_bp
    from app.api.favorites import favorites_bp
    from app.api.admin import admin_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(posts_bp, url_prefix='/api/posts')
    app.register_blueprint(categories_bp, url_prefix='/api/categories')
    app.register_blueprint(favorites_bp, url_prefix='/api/favorites')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')

    return app