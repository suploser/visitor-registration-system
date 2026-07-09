import uuid
import secrets
from datetime import datetime, timedelta
from models import db


class Approver(db.Model):
    """审批人表"""
    __tablename__ = 'approvers'
    __table_args__ = (
        db.UniqueConstraint('openid', 'role', name='uq_openid_role'),  # 同一人可注册不同角色，但不能重复注册同一角色
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    openid = db.Column(db.String(100), nullable=False)  # 移除unique=True，允许同一openid拥有多个角色
    name = db.Column(db.String(50), nullable=False)
    department = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(10), nullable=False)  # 'level1' or 'level2'
    register_token = db.Column(db.String(64), unique=True)
    token_expires = db.Column(db.DateTime)
    is_registered = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, server_default=db.func.current_timestamp())

    @staticmethod
    def generate_register_token():
        """生成注册token"""
        return secrets.token_urlsafe(32)

    def is_token_valid(self):
        """检查注册token是否有效"""
        return self.token_expires and self.token_expires > datetime.now()

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'department': self.department,
            'role': self.role,
            'is_registered': self.is_registered,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else '',
        }
