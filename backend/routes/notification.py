"""
订阅消息管理接口
"""
import os
from flask import Blueprint, request, jsonify, g
from datetime import datetime

from models import db
from models.notification import NotificationSubscription
from routes.auth import login_required

notification_bp = Blueprint('notification', __name__)


@notification_bp.route('/templates', methods=['GET'])
def get_templates():
    """
    返回系统配置的订阅消息模板 ID 列表。
    前端需调用 wx.requestSubscribeMessage 时用到。

    不需要登录态（前端在调 wx.requestSubscribeMessage 前需知道 tmplIds）。
    """
    templates = []

    approval_tmpl = os.environ.get('WX_TMPL_APPROVAL_NOTICE', '')
    result_tmpl = os.environ.get('WX_TMPL_RESULT_NOTICE', '')

    if approval_tmpl:
        templates.append({
            'template_id': approval_tmpl,
            'key': 'APPROVAL_NOTICE',
            'name': '待审批通知',
            'for_role': 'level1,level2',
        })
    if result_tmpl:
        templates.append({
            'template_id': result_tmpl,
            'key': 'RESULT_NOTICE',
            'name': '审批结果通知',
            'for_role': 'visitor',
        })

    return jsonify({
        'code': 0,
        'data': templates,
    })


@notification_bp.route('/subscribe', methods=['POST'])
@login_required
def report_subscription():
    """
    上报微信订阅消息授权结果。

    前端在 wx.requestSubscribeMessage 成功回调中调用。

    Body:
        subscriptions: [
            {template_id: 'xxx', status: 'accept'/'reject'},
            ...
        ]
    """
    openid = g.current_user.get('openid', '')
    if not openid:
        return jsonify({'code': 400, 'message': '无法获取用户身份'}), 400

    data = request.get_json() or {}
    subscriptions = data.get('subscriptions', [])

    if not subscriptions:
        return jsonify({'code': 400, 'message': '缺少 subscriptions 参数'}), 400

    accepted_count = 0
    for item in subscriptions:
        template_id = item.get('template_id', '')
        status = item.get('status', '')

        if not template_id:
            continue

        if status == 'accept':
            # 创建新的订阅记录
            sub = NotificationSubscription(
                openid=openid,
                template_id=template_id,
                status='active',
            )
            db.session.add(sub)
            accepted_count += 1

    db.session.commit()

    return jsonify({
        'code': 0,
        'message': f'订阅成功，共 {accepted_count} 个模板',
        'data': {'accepted_count': accepted_count},
    })


@notification_bp.route('/status', methods=['GET'])
@login_required
def get_subscription_status():
    """
    查询当前用户各模板的订阅状态（用于判断是否需要提示用户重新订阅）。
    """
    openid = g.current_user.get('openid', '')
    if not openid:
        return jsonify({'code': 400, 'message': '无法获取用户身份'}), 400

    # 返回所有模板的订阅情况
    approval_tmpl = os.environ.get('WX_TMPL_APPROVAL_NOTICE', '')
    result_tmpl = os.environ.get('WX_TMPL_RESULT_NOTICE', '')

    templates = []
    for tmpl_id, key, name in [
        (approval_tmpl, 'APPROVAL_NOTICE', '待审批通知'),
        (result_tmpl, 'RESULT_NOTICE', '审批结果通知'),
    ]:
        if not tmpl_id:
            continue
        active_count = NotificationSubscription.query.filter(
            NotificationSubscription.openid == openid,
            NotificationSubscription.template_id == tmpl_id,
            NotificationSubscription.status == 'active',
        ).count()
        templates.append({
            'template_id': tmpl_id,
            'key': key,
            'name': name,
            'active_count': active_count,
            'has_active': active_count > 0,
        })

    return jsonify({
        'code': 0,
        'data': templates,
    })
