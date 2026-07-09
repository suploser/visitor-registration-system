"""
应用配置管理
通过环境变量 ENV 切换测试/生产环境
  ENV=development  测试环境
  ENV=production   生产环境
"""
import os
from datetime import timedelta

ENV = os.environ.get('ENV', 'development')


class Config:
    """基础配置"""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'visitor-system-secret-key-change-in-production')
    JWT_EXPIRATION_HOURS = int(os.environ.get('JWT_EXPIRATION_HOURS', '2'))
    JWT_ALGORITHM = 'HS256'

    # AES 加密密钥（32字节用于AES-256）
    AES_KEY = os.environ.get('AES_KEY', 'visitor-aes-key-32bytes-demo!!')  # 生产环境必须修改
    AES_IV = os.environ.get('AES_IV', 'visitor-iv-16byte')  # 16字节IV

    # 会话过期时间
    SESSION_EXPIRATION_HOURS = 2

    # Excel 导出密码
    EXCEL_PASSWORD = os.environ.get('EXCEL_PASSWORD', 'visitor2024')

    # 管理员密码策略
    PASSWORD_MIN_LENGTH = 8
    PASSWORD_REQUIRE_COMPLEXITY = True  # 大小写+数字+特殊字符至少3种
    PASSWORD_EXPIRY_DAYS = 7            # 密码7天必须修改
    ADMIN_TOKEN_EXPIRY_MINUTES = 10     # 管理员登录超时10分钟

    # SQLAlchemy
    SQLALCHEMY_TRACK_MODIFICATIONS = False


class DevelopmentConfig(Config):
    """测试环境配置"""
    DEBUG = True
    DB_USER = os.environ.get('DB_USER', 'root')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', 'root')  # 本地MySQL默认通常无密码
    DB_HOST = os.environ.get('DB_HOST', '127.0.0.1')
    DB_PORT = os.environ.get('DB_PORT', '3306')
    DB_NAME = os.environ.get('DB_NAME', 'visitor_dev')

    SQLALCHEMY_DATABASE_URI = (
        f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
        '?charset=utf8mb4'
    )


class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False
    DB_USER = os.environ.get('DB_USER', 'visitor')
    DB_PASSWORD = os.environ.get('DB_PASSWORD')
    DB_HOST = os.environ.get('DB_HOST', '127.0.0.1')
    DB_PORT = os.environ.get('DB_PORT', '3306')
    DB_NAME = os.environ.get('DB_NAME', 'visitor_prod')

    SQLALCHEMY_DATABASE_URI = (
        f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
        '?charset=utf8mb4'
    )


config_map = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
}


def get_config():
    """获取当前环境配置"""
    config_class = config_map.get(ENV, DevelopmentConfig)
    config_class.ENV = ENV  # 将环境名注入配置对象，供健康检查等使用
    return config_class
