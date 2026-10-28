import os
from dotenv import load_dotenv

# 从 .env 文件加载环境变量（仅开发环境使用）
load_dotenv()


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///blog.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # JWT 认证配置
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'dev-jwt-secret-key')
    JWT_ACCESS_TOKEN_EXPIRES = int(os.environ.get('JWT_EXPIRES', 86400))  # 秒

    # 允许跨域的来源（Vue 开发服务器）
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', 'http://localhost:5173')


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


# 根据环境变量选择配置
config_map = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig,
}