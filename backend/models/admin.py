from datetime import datetime, timedelta
from models import db
from services.crypto import hash_password


class Admin(db.Model):
    """管理员表"""
    __tablename__ = 'admins'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(50), nullable=False, unique=True)
    password_hash = db.Column(db.String(200), nullable=False)
    last_password_change = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, server_default=db.func.current_timestamp())

    # 登录安全字段
    failed_attempts = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime)
    session_token = db.Column(db.String(64))

    def set_password(self, password):
        """设置密码哈希"""
        self.password_hash = hash_password(password)
        self.last_password_change = datetime.utcnow()

    def is_password_expired(self, expiry_days: int = 7) -> bool:
        """检查密码是否已过期（超过指定天数未修改）"""
        if not self.last_password_change:
            return True
        return datetime.utcnow() - self.last_password_change > timedelta(days=expiry_days)

    def is_locked(self) -> bool:
        """检查账户是否处于锁定状态（锁定过期自动清除）"""
        if not self.locked_until:
            return False
        if datetime.utcnow() >= self.locked_until:
            self.locked_until = None
            self.failed_attempts = 0
            return False
        return True

    def lockout_remaining_minutes(self) -> int:
        """返回剩余锁定分钟数（向上取整，最小 1）"""
        if not self.locked_until:
            return 0
        remaining = (self.locked_until - datetime.utcnow()).total_seconds()
        if remaining <= 0:
            return 0
        return max(1, int(remaining / 60) + (1 if remaining % 60 > 0 else 0))

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'last_password_change': self.last_password_change.strftime('%Y-%m-%d %H:%M:%S')
                if self.last_password_change else '',
        }


class SystemConfig(db.Model):
    """系统配置表"""
    __tablename__ = 'system_config'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    config_key = db.Column(db.String(100), nullable=False, unique=True)
    config_value = db.Column(db.Text)
    updated_at = db.Column(db.DateTime, server_default=db.func.current_timestamp(),
                           onupdate=db.func.current_timestamp())

    def to_dict(self):
        return {
            'key': self.config_key,
            'value': self.config_value,
        }


class ApprovalRecord(db.Model):
    """审批记录表"""
    __tablename__ = 'approval_records'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    visitor_id = db.Column(db.Integer, db.ForeignKey('visitors.id',
                           ondelete='CASCADE'), nullable=False)
    approver_id = db.Column(db.Integer, db.ForeignKey('approvers.id',
                            ondelete='CASCADE'), nullable=False)
    approver_name = db.Column(db.String(50), nullable=False)
    approver_role = db.Column(db.String(10), nullable=False)
    result = db.Column(db.String(10), nullable=False)  # 'approved' or 'rejected'
    comment = db.Column(db.String(500))
    approved_at = db.Column(db.DateTime, server_default=db.func.current_timestamp())

    def to_dict(self):
        return {
            'id': self.id,
            'visitor_id': self.visitor_id,
            'approver_id': self.approver_id,
            'approver_name': self.approver_name,
            'approver_role': self.approver_role,
            'result': self.result,
            'comment': self.comment,
            'approved_at': self.approved_at.strftime('%Y-%m-%d %H:%M:%S')
                if self.approved_at else '',
        }
