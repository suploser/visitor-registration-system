"""
Flask 应用入口
"""
import os
import sys
import click as _click
from datetime import datetime, timedelta

from flask import Flask
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler

from config import get_config

# 创建 Flask 应用
app = Flask(__name__, static_folder='../admin/static', static_url_path='/admin/static')

# 加载配置
config = get_config()
app.config.from_object(config)

# 启用 CORS
CORS(app, supports_credentials=True)

# 初始化数据库
from models import db
db.init_app(app)

# 注册路由
from routes.auth import auth_bp
from routes.visitor import visitor_bp
from routes.approver import approver_bp
from routes.admin import admin_bp
from routes.system import system_bp

app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(visitor_bp, url_prefix='/api/visitor')
app.register_blueprint(approver_bp, url_prefix='/api/approver')
app.register_blueprint(admin_bp, url_prefix='/api/admin')
app.register_blueprint(system_bp, url_prefix='/api')


# ========== 定时任务：清理过期会话 ==========

def cleanup_expired_sessions():
    """清理过期的访客会话"""
    from models.visitor import Visitor
    with app.app_context():
        now = datetime.now()
        expired = Visitor.query.filter(
            Visitor.session_expires < now,
            Visitor.session_expires.isnot(None)
        ).all()
        for v in expired:
            v.session_expires = None
            if v.status in ('pending', 'level1_approved'):
                v.status = 'rejected'
                v.reject_reason = '会话已过期'
        db.session.commit()
        if expired:
            print(f'[Cleanup] {len(expired)} expired sessions cleaned at {now}')


scheduler = BackgroundScheduler()
scheduler.add_job(cleanup_expired_sessions, 'interval', minutes=10, id='cleanup')
scheduler.start()


# ========== 健康检查 ==========

@app.route('/api/health')
def health_check():
    return {'status': 'ok', 'env': config.ENV if hasattr(config, 'ENV') else 'unknown'}


# ========== 管理后台页面 ==========

from flask import send_from_directory

@app.route('/admin/')
@app.route('/admin/<path:filename>')
def serve_admin(filename='login.html'):
    """服务管理后台静态页面"""
    from flask import make_response
    admin_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'admin')
    response = make_response(send_from_directory(admin_dir, filename))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


# ========== 初始化数据库表 ==========

@app.cli.command('init-db')
def init_db_command():
    """创建所有数据库表"""
    with app.app_context():
        db.create_all()
        print('All database tables created.')


@app.cli.command('reset-admin-password')
@_click.option('--password', default=None, help='新密码（不指定则使用默认密码 Admin@123456）')
def reset_admin_password_command(password=None):
    """重置管理员密码
    用法: flask --app app reset-admin-password
          flask --app app reset-admin-password --password 新密码
    """
    from models.admin import Admin

    with app.app_context():
        admin = Admin.query.filter_by(username='admin').first()
        if not admin:
            print('管理员账号 admin 不存在，请先运行 flask --app app seed-db')
            return

        new_password = password or 'Admin@123456'

        from utils.validators import validate_password
        ok, err = validate_password(new_password)
        if not ok:
            print(f'密码不符合要求: {err}')
            return

        admin.set_password(new_password)
        db.session.commit()
        print(f'管理员 admin 密码已重置为: {new_password}')
        print('请登录后立即修改密码。')


@app.cli.command('seed-db')
def seed_db_command():
    """初始化种子数据"""
    with app.app_context():
        from models.department import Department, Level2Department
        from models.admin import Admin, SystemConfig
        from services.crypto import hash_password

        # 部门列表
        depts = ['行政部', '财务部', '技术部', '市场部', '人力资源部',
                 '研发部', '生产部', '质量管理部', '采购部', '销售部']
        for name in depts:
            if not Department.query.filter_by(name=name).first():
                db.session.add(Department(name=name))

        # 二级审批人部门
        if not Level2Department.query.filter_by(name='安全保卫部').first():
            db.session.add(Level2Department(name='安全保卫部'))

        # 管理员
        if not Admin.query.filter_by(username='admin').first():
            admin = Admin(username='admin')
            admin.set_password('Admin@123456')
            db.session.add(admin)

        # 系统配置
        configs = {
            'welcome_message': '各位领导，合作伙伴，访客，您正在使用访客登记系统，请知悉相关管理规定。',
            'visitor_notice': '<h3>访客告知书</h3><p>欢迎您来访我单位。为保障单位安全和工作秩序，请您遵守以下规定：</p><ol><li>请如实填写个人信息，不得冒用他人身份。</li><li>进入园区后请佩戴访客标识，在指定区域内活动。</li><li>未经许可不得拍照、录像或录音。</li><li>请遵守单位的保密制度，不得泄露在访问过程中获知的任何信息。</li><li>携带信息设备的，请主动登记并接受检查。</li><li>离开时请交还访客标识并办理离园手续。</li><li>违反以上规定者，单位有权终止其访问并追究相关责任。</li></ol>',
            'home_bg_images': '["/images/hero-bg.png"]',
            'company_scroll_images': '["/images/company-1.png","/images/company-2.png","/images/company-3.png"]',
            'excel_password': 'visitor2024',
        }
        for key, value in configs.items():
            if not SystemConfig.query.filter_by(config_key=key).first():
                db.session.add(SystemConfig(config_key=key, config_value=value))

        db.session.commit()
        print('Seed data inserted successfully.')


# ========== 启动入口 ==========

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print('Database tables ensured.')

    app.run(
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 5000)),
        debug=config.DEBUG
    )
