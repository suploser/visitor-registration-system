from models import db
from services.crypto import aes_encrypt, aes_decrypt, mask_id_number, mask_phone


class Visitor(db.Model):
    """访客登记主表"""
    __tablename__ = 'visitors'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(200), nullable=False)       # AES加密
    id_number = db.Column(db.String(200), nullable=False)    # AES加密
    host_name = db.Column(db.String(50), nullable=False)
    host_department = db.Column(db.String(100), nullable=False)
    visit_start = db.Column(db.DateTime, nullable=False)
    visit_end = db.Column(db.DateTime, nullable=False)
    visit_location = db.Column(db.String(200), nullable=False)
    visit_purpose = db.Column(db.String(500), nullable=False)
    visitor_count = db.Column(db.Integer, default=1)
    has_device = db.Column(db.Boolean, default=False)
    device_info = db.Column(db.String(500))
    license_plates = db.Column(db.Text, default='[]')  # JSON数组，支持多辆车
    openid = db.Column(db.String(100))
    status = db.Column(db.String(20), default='pending')
    reject_reason = db.Column(db.String(500))
    session_expires = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, server_default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, server_default=db.func.current_timestamp(),
                           onupdate=db.func.current_timestamp())

    companions = db.relationship('Companion', backref='visitor', lazy=True,
                                 cascade='all, delete-orphan')

    def get_decrypted_phone(self):
        """获取解密后的手机号"""
        return aes_decrypt(self.phone)

    def get_decrypted_id_number(self):
        """获取解密后的身份证号"""
        return aes_decrypt(self.id_number)

    def get_license_plates(self):
        """获取车牌号列表"""
        import json
        try:
            return json.loads(self.license_plates or '[]')
        except (json.JSONDecodeError, TypeError):
            return [self.license_plates] if self.license_plates else []

    def set_license_plates(self, plates: list):
        """设置车牌号列表（JSON数组存储）"""
        import json
        self.license_plates = json.dumps(plates, ensure_ascii=False)

    def set_phone(self, plain_phone):
        """加密存储手机号"""
        self.phone = aes_encrypt(plain_phone)

    def set_id_number(self, plain_id):
        """加密存储身份证号"""
        self.id_number = aes_encrypt(plain_id)

    def to_dict(self, decrypt=False):
        """转为字典，可选择解密"""
        data = {
            'id': self.id,
            'name': self.name,
            'host_name': self.host_name,
            'host_department': self.host_department,
            'visit_start': self.visit_start.strftime('%Y-%m-%d %H:%M') if self.visit_start else '',
            'visit_end': self.visit_end.strftime('%Y-%m-%d %H:%M') if self.visit_end else '',
            'visit_location': self.visit_location,
            'visit_purpose': self.visit_purpose,
            'visitor_count': self.visitor_count,
            'has_device': self.has_device,
            'device_info': self.device_info,
            'license_plates': self.get_license_plates(),
            'status': self.status,
            'reject_reason': self.reject_reason,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else '',
        }
        if decrypt:
            data['phone'] = self.get_decrypted_phone()
            data['id_number'] = self.get_decrypted_id_number()
        else:
            # 脱敏展示
            data['phone'] = mask_phone(self.get_decrypted_phone())
            data['id_number'] = mask_id_number(self.get_decrypted_id_number())

        data['companions'] = [c.to_dict(decrypt=decrypt) for c in self.companions]
        return data


class Companion(db.Model):
    """同行人表"""
    __tablename__ = 'companions'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    visitor_id = db.Column(db.Integer, db.ForeignKey('visitors.id',
                           ondelete='CASCADE'), nullable=False)
    name = db.Column(db.String(50), nullable=False)
    id_number = db.Column(db.String(200), nullable=False)  # AES加密

    def get_decrypted_id_number(self):
        return aes_decrypt(self.id_number)

    def set_id_number(self, plain_id):
        self.id_number = aes_encrypt(plain_id)

    def to_dict(self, decrypt=False):
        data = {
            'id': self.id,
            'name': self.name,
        }
        if decrypt:
            data['id_number'] = self.get_decrypted_id_number()
        else:
            data['id_number'] = mask_id_number(self.get_decrypted_id_number())
        return data
