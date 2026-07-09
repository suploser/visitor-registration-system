"""验证码模型 — 审批人录入链接的校验码"""
from datetime import datetime
from models import db


class VerificationCode(db.Model):
    """审批人录入验证码表"""
    __tablename__ = 'verification_codes'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    code = db.Column(db.String(10), nullable=False)
    role = db.Column(db.String(10), nullable=False)  # 'level1' or 'level2'
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.current_timestamp())

    def is_valid(self):
        """验证码是否在有效期内"""
        return self.expires_at and self.expires_at > datetime.utcnow()

    def to_dict(self):
        return {
            'id': self.id,
            'code': self.code,
            'role': self.role,
            'role_label': '一级审批人' if self.role == 'level1' else '二级审批人',
            'expires_at': self.expires_at.strftime('%Y-%m-%d %H:%M:%S') if self.expires_at else '',
            'is_valid': self.is_valid(),
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else '',
        }
