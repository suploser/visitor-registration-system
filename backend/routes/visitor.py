"""
访客相关接口
"""
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, g

from models import db
from models.visitor import Visitor, Companion
from models.department import Department
from models.approver import Approver
from models.admin import SystemConfig
from routes.auth import login_required
from services.approval import ApprovalService
from utils.validators import validate_phone, validate_id_number, validate_required, validate_license_plate
from config import get_config

visitor_bp = Blueprint('visitor', __name__)
config = get_config()


@visitor_bp.route('/departments', methods=['GET'])
def get_departments():
    """获取接待人部门列表"""
    depts = Department.query.order_by(Department.id).all()
    return jsonify({
        'code': 0,
        'data': [d.to_dict() for d in depts]
    })


@visitor_bp.route('/register', methods=['POST'])
@login_required
def register_visitor():
    """
    访客登记提交
    """
    data = request.get_json() or {}

    # 必填字段验证
    required_fields = [
        ('name', '姓名'),
        ('phone', '手机号'),
        ('id_number', '身份证号码'),
        ('host_name', '接待人'),
        ('host_department', '接待人部门'),
        ('visit_start', '访问开始时间'),
        ('visit_end', '访问结束时间'),
        ('visit_location', '访问地点'),
        ('visit_purpose', '访问目的'),
    ]

    for field, label in required_fields:
        ok, err = validate_required(data.get(field), label)
        if not ok:
            return jsonify({'code': 400, 'message': err}), 400

    # 手机号验证
    ok, err = validate_phone(data['phone'])
    if not ok:
        return jsonify({'code': 400, 'message': err}), 400

    # 身份证号验证
    ok, err = validate_id_number(data['id_number'])
    if not ok:
        return jsonify({'code': 400, 'message': err}), 400

    # 车牌号验证（JSON数组）
    license_plates = data.get('license_plates', [])
    if license_plates:
        for plate in license_plates:
            if plate:
                ok, err = validate_license_plate(plate)
                if not ok:
                    return jsonify({'code': 400, 'message': f'车牌号"{plate}"{err}'}), 400

    # 检查同一openid是否已有未过期的进行中申请（pending/level1_approved）
    existing = Visitor.query.filter(
        Visitor.openid == g.current_user['openid'],
        Visitor.session_expires > datetime.now(),
        Visitor.status.in_(['pending', 'level1_approved'])
    ).first()

    if existing:
        return jsonify({
            'code': 400,
            'message': '您已有未完成的登记申请，请等待审批结果'
        }), 400

    # 查找是否有被拒绝的记录，如果有则更新而非新建
    rejected = Visitor.query.filter(
        Visitor.openid == g.current_user['openid'],
        Visitor.status == 'rejected'
    ).order_by(Visitor.created_at.desc()).first()

    if rejected:
        visitor = rejected
        # 删除旧的同行人
        Companion.query.filter_by(visitor_id=visitor.id).delete()
    else:
        visitor = Visitor(openid=g.current_user['openid'])
        db.session.add(visitor)

    # 来访人数（前端可能传字符串，强制转int）
    try:
        visitor_count = int(data.get('visitor_count', 1))
    except (ValueError, TypeError):
        visitor_count = 1

    # 更新字段
    visitor.name = data['name'].strip()
    visitor.host_name = data['host_name'].strip()
    visitor.host_department = data['host_department'].strip()
    visitor.visit_location = data['visit_location'].strip()
    visitor.visit_purpose = data['visit_purpose'].strip()
    visitor.visitor_count = visitor_count
    visitor.has_device = data.get('has_device', False)
    visitor.device_info = data.get('device_info', '').strip() if data.get('has_device') else ''
    visitor.status = 'pending'
    visitor.reject_reason = None

    # 保存车牌列表
    visitor.set_license_plates(license_plates)

    # 加密存储手机号和身份证号
    visitor.set_phone(data['phone'].strip())
    visitor.set_id_number(data['id_number'].strip())

    # 解析时间
    try:
        visitor.visit_start = datetime.strptime(data['visit_start'], '%Y-%m-%d %H:%M')
        visitor.visit_end = datetime.strptime(data['visit_end'], '%Y-%m-%d %H:%M')
    except ValueError:
        return jsonify({'code': 400, 'message': '时间格式不正确，格式为 YYYY-MM-DD HH:MM'}), 400

    if visitor.visit_end <= visitor.visit_start:
        return jsonify({'code': 400, 'message': '访问结束时间必须晚于开始时间'}), 400

    # 设置会话过期时间
    visitor.session_expires = datetime.now() + timedelta(hours=config.SESSION_EXPIRATION_HOURS)

    # 检查是否有一级审批人匹配该部门，没有则直接升至待二级审批
    from services.approval import ApprovalService
    level1 = ApprovalService.find_level1_approver(visitor.host_department)
    if not level1:
        level2 = ApprovalService.find_level2_approver()
        if level2:
            visitor.status = 'level1_approved'

    db.session.flush()  # 确保visitor.id可用

    # 处理同行人
    companions_data = data.get('companions', [])
    # 过滤掉空白的同行人
    valid_companions = [c for c in companions_data if c.get('name') and c.get('id_number')]

    # 校验来访人数与同行人数量一致
    expected_companions = visitor.visitor_count - 1
    if expected_companions < 0:
        expected_companions = 0
    if len(valid_companions) != expected_companions:
        db.session.rollback()
        return jsonify({
            'code': 400,
            'message': f'来访人数为{visitor.visitor_count}人，需填写{expected_companions}位同行人信息（当前填写了{len(valid_companions)}位）'
        }), 400

    for comp in valid_companions:
        ok, err = validate_id_number(comp['id_number'])
        if not ok:
            db.session.rollback()
            return jsonify({'code': 400, 'message': f'同行人"{comp["name"]}"{err}'}), 400

        companion = Companion(
            visitor_id=visitor.id,
            name=comp['name'].strip(),
        )
        companion.set_id_number(comp['id_number'].strip())
        db.session.add(companion)

    db.session.commit()

    return jsonify({
        'code': 0,
        'message': '登记提交成功，请等待审批',
        'data': {
            'id': visitor.id,
            'status': visitor.status,
        }
    })


@visitor_bp.route('/status', methods=['GET'])
@login_required
def get_status():
    """
    查询当前访客的登记状态
    """
    openid = g.current_user['openid']

    visitor = Visitor.query.filter(
        Visitor.openid == openid,
        Visitor.session_expires > datetime.now()
    ).order_by(Visitor.created_at.desc()).first()

    if not visitor:
        return jsonify({
            'code': 0,
            'data': {
                'has_record': False,
                'message': '暂无有效登记记录'
            }
        })

    data = visitor.to_dict(decrypt=False)

    # 查找最新审批记录
    from models.admin import ApprovalRecord
    records = ApprovalRecord.query.filter_by(
        visitor_id=visitor.id
    ).order_by(ApprovalRecord.approved_at.desc()).all()
    data['approval_records'] = [r.to_dict() for r in records]

    return jsonify({
        'code': 0,
        'data': {
            'has_record': True,
            'visitor': data,
            'session_expires': visitor.session_expires.strftime('%Y-%m-%d %H:%M:%S')
                if visitor.session_expires else '',
        }
    })


@visitor_bp.route('/credential', methods=['GET'])
@login_required
def get_credential():
    """
    获取审批通过凭证
    仅当 status=approved 且会话未过期时返回
    """
    openid = g.current_user['openid']

    visitor = Visitor.query.filter(
        Visitor.openid == openid,
        Visitor.status == 'approved',
        Visitor.session_expires > datetime.now()
    ).order_by(Visitor.created_at.desc()).first()

    if not visitor:
        return jsonify({
            'code': 404,
            'message': '未找到有效通行凭证，可能已过期或尚未通过审批'
        }), 404

    credential = {
        'visitor_name': visitor.name,
        'visitor_count': visitor.visitor_count,
        'host_name': visitor.host_name,
        'host_department': visitor.host_department,
        'visit_location': visitor.visit_location,
        'visit_start': visitor.visit_start.strftime('%Y-%m-%d %H:%M'),
        'visit_end': visitor.visit_end.strftime('%Y-%m-%d %H:%M'),
        'license_plates': '、'.join(visitor.get_license_plates()),
        'approved_at': visitor.updated_at.strftime('%Y-%m-%d %H:%M:%S') if visitor.updated_at else '',
        'expires_at': visitor.session_expires.strftime('%Y-%m-%d %H:%M:%S') if visitor.session_expires else '',
    }

    return jsonify({
        'code': 0,
        'data': credential
    })
