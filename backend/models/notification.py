"""
订阅消息数据模型
"""
from datetime import datetime
from models import db


class NotificationSubscription(db.Model):
    """用户订阅消息记录表"""
    __tablename__ = 'notification_subscriptions'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    openid = db.Column(db.String(100), nullable=False, comment='订阅者的微信 openid')
    template_id = db.Column(db.String(100), nullable=False, comment='订阅消息模板 ID')
    status = db.Column(db.String(20), default='active', comment='active=可用, used=已消耗, expired=已过期')
    created_at = db.Column(db.DateTime, server_default=db.func.current_timestamp())
    used_at = db.Column(db.DateTime, comment='使用时间')

    __table_args__ = (
        db.Index('idx_openid_template_status', 'openid', 'template_id', 'status'),
        {'comment': '微信订阅消息记录表'},
    )

    def to_dict(self):
        return {
            'id': self.id,
            'openid': self.openid,
            'template_id': self.template_id,
            'status': self.status,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else '',
        }

    @classmethod
    def get_active_subscriptions(cls, openid, template_id=None):
        """获取用户未消耗的订阅记录"""
        q = cls.query.filter(
            cls.openid == openid,
            cls.status == 'active',
        )
        if template_id:
            q = q.filter(cls.template_id == template_id)
        return q.order_by(cls.created_at.desc()).all()

    @classmethod
    def consume(cls, openid, template_id):
        """消耗一条订阅记录（标记为 used），返回 True 表示有可用记录并已消耗"""
        sub = cls.query.filter(
            cls.openid == openid,
            cls.template_id == template_id,
            cls.status == 'active',
        ).order_by(cls.created_at.asc()).first()
        if not sub:
            return False
        sub.status = 'used'
        sub.used_at = datetime.utcnow()
        return True
