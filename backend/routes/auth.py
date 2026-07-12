"""
认证相关接口
- 微信登录
- 管理员登录
"""
import uuid
from datetime import datetime, timedelta
from functools import wraps

import jwt
from flask import Blueprint, request, jsonify, g

from models import db
from models.admin import Admin
from models.approver import Approver
from config import get_config

auth_bp = Blueprint('auth', __name__)
config = get_config()


def generate_jwt(payload: dict, expires_hours: int = None, expires_minutes: int = None) -> str:
    """生成 JWT token（支持小时或分钟作为过期时间）"""
    if expires_minutes is not None:
        exp = datetime.utcnow() + timedelta(minutes=expires_minutes)
    elif expires_hours is not None:
        exp = datetime.utcnow() + timedelta(hours=expires_hours)
    else:
        exp = datetime.utcnow() + timedelta(hours=config.JWT_EXPIRATION_HOURS)

    payload['exp'] = exp
    payload['iat'] = datetime.utcnow()
    return jwt.encode(payload, config.SECRET_KEY, algorithm=config.JWT_ALGORITHM)


def decode_jwt(token: str) -> dict:
    """解析 JWT token"""
    try:
        return jwt.decode(token, config.SECRET_KEY, algorithms=[config.JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def login_required(f):
    """JWT 认证装饰器"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return jsonify({'code': 401, 'message': '请先登录'}), 401

        payload = decode_jwt(token)
        if not payload:
            return jsonify({'code': 401, 'message': '登录已过期，请重新登录'}), 401

        g.current_user = payload
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    """管理员认证装饰器（含密码过期检查+单会话强制）"""
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if g.current_user.get('role') != 'admin':
            return jsonify({'code': 403, 'message': '需要管理员权限'}), 403

        # --- 单会话强制检查（新登录踢旧会话）---
        jwt_session_token = g.current_user.get('session_token')
        if jwt_session_token:
            admin = Admin.query.get(g.current_user.get('user_id'))
            if admin and admin.session_token and admin.session_token != jwt_session_token:
                return jsonify({
                    'code': 409,
                    'message': '管理员已在其他设备登录，您已被强制下线。',
                    'session_conflict': True,
                }), 409

        # 密码过期时仅允许调用修改密码接口
        if g.current_user.get('pw_expired'):
            if not request.path.endswith('/api/admin/password'):
                return jsonify({
                    'code': 403, 'message': '密码已过期（超过7天未修改），请先修改密码',
                    'password_expired': True
                }), 403
        return f(*args, **kwargs)
    return decorated


def approver_required(f):
    """审批人认证装饰器"""
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if g.current_user.get('role') not in ('level1', 'level2'):
            return jsonify({'code': 403, 'message': '需要审批人权限'}), 403
        return f(*args, **kwargs)
    return decorated


@auth_bp.route('/wechat-login', methods=['POST'])
def wechat_login():
    """
    微信登录接口
    测试环境：使用 mock openid
    生产环境：调用微信 code2Session 接口
    """
    data = request.get_json() or {}
    code = data.get('code', '')

    if config.DEBUG:
        # 测试环境：使用 mock openid
        # 优先使用前端传入的 mock_openid（持久化身份）
        # 其次使用 code 参数，最后才随机生成
        mock_openid = data.get('mock_openid', '')
        openid = mock_openid or code or f'visitor_{uuid.uuid4().hex[:8]}'
        session_key = 'mock_session_key'
    else:
        # 生产环境：真实微信接口
        # TODO: 替换为真实 AppID 和 AppSecret
        import requests
        wx_url = 'https://api.weixin.qq.com/sns/jscode2session'
        params = {
            'appid': config.WECHAT_APPID,
            'secret': config.WECHAT_SECRET,
            'js_code': code,
            'grant_type': 'authorization_code',
        }
        resp = requests.get(wx_url, params=params)
        wx_data = resp.json()
        openid = wx_data.get('openid', '')
        session_key = wx_data.get('session_key', '')

    if not openid:
        return jsonify({'code': 400, 'message': '微信登录失败'}), 400

    # 检查是否为审批人（同一openid可能有level1和level2两个角色）
    approvers = Approver.query.filter_by(openid=openid, is_registered=True).all()
    if approvers:
        # 收集所有角色（去重，如 ['level1', 'level2']）
        all_roles = list(set(a.role for a in approvers))
        # 优先取level1作为主角色（用于JWT），同时保留全部角色信息供前端展示
        approver = next((a for a in approvers if a.role == 'level1'), approvers[0])
        role = approver.role
        token = generate_jwt({
            'openid': openid,
            'role': role,
            'approver_id': approver.id,
            'name': approver.name,
            'department': approver.department,
        })
        return jsonify({
            'code': 0,
            'data': {
                'token': token,
                'role': role,
                'all_roles': all_roles,
                'name': approver.name,
                'department': approver.department,
                'is_approver': True,
            }
        })

    # 普通访客
    token = generate_jwt({
        'openid': openid,
        'role': 'visitor',
    })

    return jsonify({
        'code': 0,
        'data': {
            'token': token,
            'role': 'visitor',
            'is_approver': False,
        }
    })


@auth_bp.route('/admin-login', methods=['POST'])
def admin_login():
    """管理员登录（含密码过期检查、锁定检查、单会话强制）"""
    data = request.get_json() or {}
    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not username or not password:
        return jsonify({'code': 400, 'message': '用户名和密码不能为空'}), 400

    admin = Admin.query.filter_by(username=username).first()
    if not admin:
        return jsonify({'code': 401, 'message': '用户名或密码错误'}), 401

    # --- 锁定检查（账户级，3 次输错锁定 30 分钟）---
    if admin.is_locked():
        remaining = admin.lockout_remaining_minutes()
        db.session.commit()  # 持久化锁定过期自动清除的变更
        return jsonify({
            'code': 423,
            'message': f'账户已被锁定，请在 {remaining} 分钟后重试',
            'locked_until': admin.locked_until.isoformat() if admin.locked_until else None,
            'lockout_remaining_minutes': remaining,
        }), 423

    # --- 密码验证 ---
    from services.crypto import verify_password
    if not verify_password(password, admin.password_hash):
        admin.failed_attempts = (admin.failed_attempts or 0) + 1
        remaining_attempts = config.MAX_LOGIN_ATTEMPTS - admin.failed_attempts

        if admin.failed_attempts >= config.MAX_LOGIN_ATTEMPTS:
            admin.locked_until = datetime.utcnow() + timedelta(minutes=config.LOGIN_LOCKOUT_MINUTES)
            db.session.commit()
            return jsonify({
                'code': 423,
                'message': f'密码错误次数过多，账户已被锁定 {config.LOGIN_LOCKOUT_MINUTES} 分钟',
                'locked_until': admin.locked_until.isoformat(),
                'lockout_remaining_minutes': config.LOGIN_LOCKOUT_MINUTES,
            }), 423

        db.session.commit()
        return jsonify({
            'code': 401,
            'message': f'用户名或密码错误，还剩 {remaining_attempts} 次尝试机会',
            'remaining_attempts': remaining_attempts,
        }), 401

    # --- 登录成功：重置锁定计数器 ---
    admin.failed_attempts = 0
    admin.locked_until = None

    # --- 生成新 session_token（单会话强制：新登录踢旧会话）---
    admin.session_token = str(uuid.uuid4())
    db.session.commit()

    # 检查密码是否过期（超过7天未修改）
    password_expired = admin.is_password_expired(config.PASSWORD_EXPIRY_DAYS)

    token = generate_jwt({
        'user_id': admin.id,
        'username': admin.username,
        'role': 'admin',
        'pw_expired': password_expired,
        'session_token': admin.session_token,
    }, expires_minutes=config.ADMIN_TOKEN_EXPIRY_MINUTES)

    return jsonify({
        'code': 0,
        'data': {
            'token': token,
            'username': admin.username,
            'password_expired': password_expired,
        }
    })
