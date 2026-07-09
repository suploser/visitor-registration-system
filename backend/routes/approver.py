"""
审批人相关接口
"""
import random
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, g

from models import db
from models.approver import Approver
from models.visitor import Visitor
from models.admin import ApprovalRecord
from models.department import Department, Level2Department
from models.verification_code import VerificationCode
from routes.auth import login_required, approver_required
from services.approval import ApprovalService
from config import get_config

approver_bp = Blueprint('approver', __name__)
config = get_config()


@approver_bp.route('/register/<token>', methods=['GET'])
def check_register_token(token):
    """检查注册token有效性 + 验证码校验"""
    payload = _decode_register_token(token)
    if not payload:
        return jsonify({'code': 400, 'message': '无效的注册链接或链接已过期'}), 400

    role = payload.get('role', 'level1')

    # 验证码校验
    code = request.args.get('code', '').strip()
    if not code:
        return jsonify({
            'code': 1, 'message': '请输入验证码', 'need_verify': True,
            'role': role,
        })
    if not _verify_code(code, role):
        return jsonify({
            'code': 1, 'message': '验证码错误或已过期（有效期1小时）',
            'role': role,
        })

    return jsonify({
        'code': 0,
        'data': {
            'role': role,
            'department_options': _get_department_options(role),
        }
    })


@approver_bp.route('/register/<token>', methods=['POST'])
@login_required
def submit_register(token):
    """审批人信息录入（需JWT登录 + token验证 + 验证码校验）"""
    payload = _decode_register_token(token)
    if not payload:
        return jsonify({'code': 400, 'message': '无效的注册链接或链接已过期'}), 400

    role = payload.get('role', 'level1')
    role_label = '一级审批人' if role == 'level1' else '二级审批人'

    data = request.get_json() or {}

    # 验证码校验
    code = data.get('code', '').strip()
    if not code:
        return jsonify({'code': 400, 'message': '请输入验证码'}), 400
    if not _verify_code(code, role):
        return jsonify({'code': 400, 'message': '验证码错误或已过期（有效期5分钟）'}), 400

    name = data.get('name', '').strip()
    department = data.get('department', '').strip()

    if not name:
        return jsonify({'code': 400, 'message': '请输入姓名'}), 400
    if not department:
        return jsonify({'code': 400, 'message': '请选择部门'}), 400

    # 从 JWT 中提取 openid
    openid = g.current_user.get('openid', '')
    if not openid:
        return jsonify({'code': 400, 'message': '无法获取用户身份，请重新授权'}), 400

    # 检查该openid是否已注册为相同角色的审批人（同一人可注册不同角色）
    existing = Approver.query.filter_by(openid=openid, role=role, is_registered=True).first()
    if existing:
        return jsonify({
            'code': 0,
            'message': f'您已是{role_label}，无需重复注册',
            'data': {'role': role}
        })

    # 创建新的审批人记录（token可复用，不失效）
    approver = Approver(
        name=name,
        department=department,
        openid=openid,
        role=role,
        is_registered=True,
    )
    db.session.add(approver)
    db.session.commit()

    return jsonify({
        'code': 0,
        'message': f'审批人信息录入成功！您已成为{role_label}',
        'data': {'role': role}
    })


@approver_bp.route('/generate-link', methods=['POST'])
@login_required
def generate_register_link():
    """
    生成审批人录入链接 + 验证码
    验证码1小时有效，管理员需手动将验证码发给合法审批人
    """
    data = request.get_json() or {}
    role = data.get('role', 'level1')

    if role not in ('level1', 'level2'):
        return jsonify({'code': 400, 'message': '角色必须为 level1 或 level2'}), 400

    # 生成可复用的JWT token（仅编码角色信息，1小时有效）
    token = _generate_register_token(role)

    # 生成6位随机验证码，1小时有效
    code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
    _cleanup_expired_codes()
    vc = VerificationCode(
        code=code,
        role=role,
        expires_at=datetime.utcnow() + timedelta(hours=1),
    )
    db.session.add(vc)
    db.session.commit()

    # 小程序页面路径
    page_path = f'pages/approver-register/approver-register?token={token}'

    return jsonify({
        'code': 0,
        'data': {
            'token': token,
            'page_path': page_path,
            'verification_code': code,
            'code_expires_in': '1小时',
            'tips': '请将验证码手动发送给审批人（1小时有效）。审批人打开链接后需输入验证码方可进入录入页面。',
            'role': role,
        }
    })


@approver_bp.route('/pending', methods=['GET'])
@approver_required
def pending_approvals():
    """获取待审批列表"""
    approver = Approver.query.get(g.current_user.get('approver_id'))
    if not approver:
        return jsonify({'code': 404, 'message': '审批人不存在'}), 404

    visitors = ApprovalService.get_pending_approvals(approver)
    return jsonify({
        'code': 0,
        'data': [v.to_dict(decrypt=False) for v in visitors]
    })


@approver_bp.route('/detail/<int:visitor_id>', methods=['GET'])
@approver_required
def approval_detail(visitor_id):
    """获取审批详情（含解密信息）"""
    visitor = Visitor.query.get(visitor_id)
    if not visitor:
        return jsonify({'code': 404, 'message': '登记记录不存在'}), 404

    # 审批详情可以查看解密后的信息
    data = visitor.to_dict(decrypt=True)

    # 也返回审批历史
    records = ApprovalRecord.query.filter_by(visitor_id=visitor_id)\
        .order_by(ApprovalRecord.approved_at.desc()).all()
    data['approval_records'] = [r.to_dict() for r in records]

    return jsonify({
        'code': 0,
        'data': data
    })


@approver_bp.route('/approve', methods=['POST'])
@approver_required
def approve():
    """提交审批"""
    approver = Approver.query.get(g.current_user.get('approver_id'))
    if not approver:
        return jsonify({'code': 404, 'message': '审批人不存在'}), 404

    data = request.get_json() or {}
    visitor_id = data.get('visitor_id')
    result = data.get('result')  # 'approved' or 'rejected'
    comment = data.get('comment', '')

    if not visitor_id:
        return jsonify({'code': 400, 'message': '缺少visitor_id'}), 400
    if result not in ('approved', 'rejected'):
        return jsonify({'code': 400, 'message': '审批结果必须为approved或rejected'}), 400
    if result == 'rejected' and not comment:
        return jsonify({'code': 400, 'message': '拒绝时必须填写审批意见'}), 400

    success, message = ApprovalService.approve(visitor_id, approver, result, comment)
    if not success:
        return jsonify({'code': 400, 'message': message}), 400

    return jsonify({
        'code': 0,
        'message': message
    })


@approver_bp.route('/history', methods=['GET'])
@approver_required
def approval_history():
    """获取审批人的审批历史"""
    approver = Approver.query.get(g.current_user.get('approver_id'))
    if not approver:
        return jsonify({'code': 404, 'message': '审批人不存在'}), 404

    records = ApprovalService.get_approval_history(approver)

    result = []
    for record in records:
        visitor = Visitor.query.get(record.visitor_id)
        item = record.to_dict()
        if visitor:
            item['visitor_name'] = visitor.name
            item['host_department'] = visitor.host_department
            item['visit_start'] = visitor.visit_start.strftime('%Y-%m-%d %H:%M') \
                if visitor.visit_start else ''
        result.append(item)

    return jsonify({
        'code': 0,
        'data': result
    })


@approver_bp.route('/departments', methods=['GET'])
def get_approver_departments():
    """
    获取审批人部门列表
    一级审批人：返回接待人部门列表
    二级审批人：返回二级审批人专属部门列表
    """
    role = request.args.get('role', 'level1')

    if role == 'level2':
        depts = Level2Department.query.order_by(Level2Department.id).all()
    else:
        depts = Department.query.order_by(Department.id).all()

    return jsonify({
        'code': 0,
        'data': [d.to_dict() for d in depts]
    })


def _get_department_options(role):
    """获取部门选项"""
    if role == 'level2':
        depts = Level2Department.query.order_by(Level2Department.id).all()
    else:
        depts = Department.query.order_by(Department.id).all()
    return [{'label': d.name, 'value': d.name} for d in depts]


def _generate_register_token(role: str, expires_hours: int = 1) -> str:
    """生成可复用的注册token（JWT，编码角色信息，默认1小时有效）"""
    import jwt as pyjwt

    exp = datetime.utcnow() + timedelta(hours=expires_hours)
    payload = {
        'purpose': 'approver_register',
        'role': role,
        'exp': exp,
        'iat': datetime.utcnow(),
    }
    return pyjwt.encode(payload, config.SECRET_KEY, algorithm=config.JWT_ALGORITHM)


def _decode_register_token(token: str) -> dict:
    """解码注册token，无效或过期返回None"""
    import jwt as pyjwt
    try:
        payload = pyjwt.decode(token, config.SECRET_KEY, algorithms=[config.JWT_ALGORITHM])
        if payload.get('purpose') != 'approver_register':
            return None
        return payload
    except (pyjwt.ExpiredSignatureError, pyjwt.InvalidTokenError):
        return None


def _verify_code(code: str, role: str) -> bool:
    """验证校验码是否有效（匹配role且未过期）"""
    _cleanup_expired_codes()
    vc = VerificationCode.query.filter_by(
        code=code,
        role=role,
    ).order_by(VerificationCode.created_at.desc()).first()
    if not vc:
        return False
    return vc.is_valid()


def _cleanup_expired_codes():
    """清理过期的验证码"""
    VerificationCode.query.filter(
        VerificationCode.expires_at < datetime.utcnow()
    ).delete(synchronize_session=False)
    db.session.commit()
