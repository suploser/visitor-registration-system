"""
管理员相关接口
"""
from datetime import datetime, timedelta
from io import BytesIO
from flask import Blueprint, request, jsonify, send_file, g

from models import db
from models.admin import Admin, SystemConfig, ApprovalRecord
from models.visitor import Visitor
from models.approver import Approver
from models.department import Department, Level2Department
from models.verification_code import VerificationCode
from routes.auth import admin_required
from services.export import export_visitors_to_excel, export_approvals_to_excel, encrypt_excel
from services.crypto import verify_password, hash_password
from utils.validators import validate_password
from config import get_config

admin_bp = Blueprint('admin', __name__)
config = get_config()


@admin_bp.route('/visitors', methods=['GET'])
@admin_required
def list_visitors():
    """查看访客列表（管理后台）"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    status = request.args.get('status', '')

    query = Visitor.query
    if status:
        query = query.filter(Visitor.status == status)

    pagination = query.order_by(Visitor.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return jsonify({
        'code': 0,
        'data': {
            'items': [v.to_dict(decrypt=False) for v in pagination.items],
            'total': pagination.total,
            'page': page,
            'per_page': per_page,
            'pages': pagination.pages,
        }
    })


@admin_bp.route('/visitors/<int:visitor_id>/decrypted', methods=['POST'])
@admin_required
def get_visitor_decrypted(visitor_id):
    """查看访客解密后的手机号和身份证号（需管理员密码二次验证）"""
    data = request.get_json() or {}
    password = data.get('password', '')

    if not password:
        return jsonify({'code': 400, 'message': '请输入管理员密码'}), 400

    admin = Admin.query.get(g.current_user.get('user_id'))
    if not admin:
        return jsonify({'code': 404, 'message': '管理员不存在'}), 404

    # 锁定检查（复用登录锁定机制）
    if admin.is_locked():
        remaining = admin.lockout_remaining_minutes()
        db.session.commit()
        return jsonify({
            'code': 423,
            'message': f'账户已被锁定，请在 {remaining} 分钟后重试',
            'lockout_remaining_minutes': remaining,
        }), 423

    # 密码验证
    if not verify_password(password, admin.password_hash):
        admin.failed_attempts = (admin.failed_attempts or 0) + 1
        remaining_attempts = config.MAX_LOGIN_ATTEMPTS - admin.failed_attempts

        if admin.failed_attempts >= config.MAX_LOGIN_ATTEMPTS:
            admin.locked_until = datetime.utcnow() + timedelta(minutes=config.LOGIN_LOCKOUT_MINUTES)
            db.session.commit()
            return jsonify({
                'code': 423,
                'message': f'密码错误次数过多，账户已被锁定 {config.LOGIN_LOCKOUT_MINUTES} 分钟',
                'lockout_remaining_minutes': config.LOGIN_LOCKOUT_MINUTES,
            }), 423

        db.session.commit()
        return jsonify({
            'code': 401,
            'message': f'密码错误，还剩 {remaining_attempts} 次尝试机会',
            'remaining_attempts': remaining_attempts,
        }), 401

    # 密码正确：重置失败计数
    admin.failed_attempts = 0
    admin.locked_until = None
    db.session.commit()

    visitor = Visitor.query.get(visitor_id)
    if not visitor:
        return jsonify({'code': 404, 'message': '访客记录不存在'}), 404

    detail = visitor.to_dict(decrypt=True)
    return jsonify({'code': 0, 'data': detail})


@admin_bp.route('/approvals', methods=['GET'])
@admin_required
def list_approvals():
    """查看审批列表（管理后台）"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    pagination = db.session.query(ApprovalRecord, Visitor)\
        .join(Visitor, ApprovalRecord.visitor_id == Visitor.id)\
        .order_by(ApprovalRecord.approved_at.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)

    items = []
    for record, visitor in pagination.items:
        item = record.to_dict()
        item['visitor_name'] = visitor.name
        item['host_department'] = visitor.host_department
        items.append(item)

    return jsonify({
        'code': 0,
        'data': {
            'items': items,
            'total': pagination.total,
            'page': page,
            'per_page': per_page,
            'pages': pagination.pages,
        }
    })


@admin_bp.route('/visitors/export', methods=['GET'])
@admin_required
def export_visitors():
    """导出访客记录Excel（带密码保护）"""
    try:
        data, filename = export_visitors_to_excel()

        # 获取导出密码
        excel_pwd_config = SystemConfig.query.filter_by(config_key='excel_password').first()
        excel_password = excel_pwd_config.config_value if excel_pwd_config else config.EXCEL_PASSWORD

        # 设置密码保护
        protected_data = encrypt_excel(data, excel_password)

        return send_file(
            BytesIO(protected_data),
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename,
        )
    except Exception as e:
        return jsonify({'code': 500, 'message': f'导出失败: {str(e)}'}), 500


@admin_bp.route('/approvals/export', methods=['GET'])
@admin_required
def export_approvals():
    """导出审批记录Excel（带密码保护）"""
    try:
        data, filename = export_approvals_to_excel()

        excel_pwd_config = SystemConfig.query.filter_by(config_key='excel_password').first()
        excel_password = excel_pwd_config.config_value if excel_pwd_config else config.EXCEL_PASSWORD

        protected_data = encrypt_excel(data, excel_password)

        return send_file(
            BytesIO(protected_data),
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename,
        )
    except Exception as e:
        return jsonify({'code': 500, 'message': f'导出失败: {str(e)}'}), 500


@admin_bp.route('/password', methods=['PUT'])
@admin_required
def change_password():
    """修改管理员密码（密码过期时强制调用此接口）"""
    data = request.get_json() or {}
    old_password = data.get('old_password', '')
    new_password = data.get('new_password', '')

    if not old_password or not new_password:
        return jsonify({'code': 400, 'message': '旧密码和新密码不能为空'}), 400

    # 验证新密码复杂度
    ok, err = validate_password(new_password)
    if not ok:
        return jsonify({'code': 400, 'message': err}), 400

    admin = Admin.query.get(g.current_user.get('user_id'))
    if not admin:
        return jsonify({'code': 404, 'message': '管理员不存在'}), 404

    # 验证旧密码
    if not verify_password(old_password, admin.password_hash):
        return jsonify({'code': 400, 'message': '旧密码不正确'}), 400

    admin.set_password(new_password)
    db.session.commit()

    # 密码修改后签发新token（清除pw_expired标记，保持当前session_token）
    from routes.auth import generate_jwt
    new_token = generate_jwt({
        'user_id': admin.id,
        'username': admin.username,
        'role': 'admin',
        'pw_expired': False,
        'session_token': admin.session_token,
    }, expires_minutes=config.ADMIN_TOKEN_EXPIRY_MINUTES)

    return jsonify({
        'code': 0,
        'message': '密码修改成功',
        'data': {'token': new_token}
    })


@admin_bp.route('/departments', methods=['POST'])
@admin_required
def add_department():
    """添加部门"""
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    if not name:
        return jsonify({'code': 400, 'message': '部门名称不能为空'}), 400

    if Department.query.filter_by(name=name).first():
        return jsonify({'code': 400, 'message': '该部门已存在'}), 400

    db.session.add(Department(name=name))
    db.session.commit()
    return jsonify({'code': 0, 'message': '部门添加成功'})


@admin_bp.route('/departments/<int:dept_id>', methods=['DELETE'])
@admin_required
def delete_department(dept_id):
    """删除部门"""
    dept = Department.query.get(dept_id)
    if not dept:
        return jsonify({'code': 404, 'message': '部门不存在'}), 404
    db.session.delete(dept)
    db.session.commit()
    return jsonify({'code': 0, 'message': '部门已删除'})


@admin_bp.route('/level2-departments', methods=['POST'])
@admin_required
def add_level2_department():
    """添加二级审批人部门（仅允许存在一个）"""
    # 检查是否已存在
    existing = Level2Department.query.first()
    if existing:
        return jsonify({'code': 400, 'message': f'二级审批人部门已存在（{existing.name}），仅允许设置一个，请先删除旧部门'}), 400

    data = request.get_json() or {}
    name = data.get('name', '').strip()
    if not name:
        return jsonify({'code': 400, 'message': '部门名称不能为空'}), 400

    if Level2Department.query.filter_by(name=name).first():
        return jsonify({'code': 400, 'message': '该部门已存在'}), 400

    db.session.add(Level2Department(name=name))
    db.session.commit()
    return jsonify({'code': 0, 'message': '二级审批人部门添加成功'})


@admin_bp.route('/level2-departments/<int:dept_id>', methods=['DELETE'])
@admin_required
def delete_level2_department(dept_id):
    """删除二级审批人部门"""
    dept = Level2Department.query.get(dept_id)
    if not dept:
        return jsonify({'code': 404, 'message': '部门不存在'}), 404
    db.session.delete(dept)
    db.session.commit()
    return jsonify({'code': 0, 'message': '二级审批人部门已删除'})


@admin_bp.route('/approvers', methods=['GET'])
@admin_required
def list_approvers():
    """查看所有审批人"""
    approvers = Approver.query.order_by(Approver.role, Approver.created_at.desc()).all()
    return jsonify({
        'code': 0,
        'data': [a.to_dict() for a in approvers]
    })


@admin_bp.route('/approvers/<int:approver_id>', methods=['DELETE'])
@admin_required
def delete_approver(approver_id):
    """删除审批人"""
    approver = Approver.query.get(approver_id)
    if not approver:
        return jsonify({'code': 404, 'message': '审批人不存在'}), 404
    db.session.delete(approver)
    db.session.commit()
    return jsonify({'code': 0, 'message': '审批人已删除'})


@admin_bp.route('/verification-codes', methods=['GET'])
@admin_required
def list_verification_codes():
    """查看有效验证码列表（管理员可手动发给审批人）"""
    from datetime import datetime as dt
    # 清理过期
    VerificationCode.query.filter(
        VerificationCode.expires_at < dt.utcnow()
    ).delete(synchronize_session=False)
    db.session.commit()

    codes = VerificationCode.query.order_by(
        VerificationCode.created_at.desc()
    ).limit(20).all()

    return jsonify({
        'code': 0,
        'data': [c.to_dict() for c in codes]
    })
