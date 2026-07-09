"""
系统配置相关接口
"""
from flask import Blueprint, request, jsonify

from models import db
from models.admin import SystemConfig
from routes.auth import admin_required

system_bp = Blueprint('system', __name__)


@system_bp.route('/config/public', methods=['GET'])
def get_public_config():
    """获取公开配置（欢迎语、告知书等）"""
    configs = SystemConfig.query.filter(
        SystemConfig.config_key.in_(['welcome_message', 'visitor_notice',
                                      'home_bg_images', 'company_scroll_images'])
    ).all()

    result = {}
    for c in configs:
        result[c.config_key] = c.config_value or ''

    return jsonify({
        'code': 0,
        'data': result
    })


@system_bp.route('/admin/config', methods=['GET'])
@admin_required
def get_all_config():
    """获取所有系统配置（管理员）"""
    configs = SystemConfig.query.all()
    return jsonify({
        'code': 0,
        'data': {c.config_key: c.config_value for c in configs}
    })


@system_bp.route('/admin/config', methods=['PUT'])
@admin_required
def update_config():
    """更新系统配置"""
    data = request.get_json() or {}

    for key, value in data.items():
        config_item = SystemConfig.query.filter_by(config_key=key).first()
        if config_item:
            config_item.config_value = str(value) if value is not None else ''
        else:
            db.session.add(SystemConfig(config_key=key, config_value=str(value) if value is not None else ''))

    db.session.commit()
    return jsonify({'code': 0, 'message': '配置更新成功'})
