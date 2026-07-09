"""
加密解密服务
- AES-256-CBC 加密用于身份证号和手机号存储
- bcrypt 用于管理员密码哈希
"""
import base64
import hashlib
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
import bcrypt

from config import get_config

config = get_config()


def _get_aes_cipher():
    """获取AES cipher实例"""
    # 确保密钥为32字节
    key = hashlib.sha256(config.AES_KEY.encode()).digest()
    iv = config.AES_IV.encode()[:16].ljust(16, b'\x00')
    return key, iv


def aes_encrypt(plaintext: str) -> str:
    """
    AES-256-CBC 加密
    返回 base64 编码的密文
    """
    if not plaintext:
        return ''
    key, iv = _get_aes_cipher()
    cipher = AES.new(key, AES.MODE_CBC, iv)
    padded = pad(plaintext.encode('utf-8'), AES.block_size)
    encrypted = cipher.encrypt(padded)
    return base64.b64encode(encrypted).decode('utf-8')


def aes_decrypt(ciphertext: str) -> str:
    """
    AES-256-CBC 解密
    返回明文
    """
    if not ciphertext:
        return ''
    key, iv = _get_aes_cipher()
    cipher = AES.new(key, AES.MODE_CBC, iv)
    try:
        decrypted = cipher.decrypt(base64.b64decode(ciphertext))
        return unpad(decrypted, AES.block_size).decode('utf-8')
    except Exception:
        return '[解密失败]'


def hash_password(password: str) -> str:
    """bcrypt 密码哈希"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(password: str, password_hash: str) -> bool:
    """验证 bcrypt 密码"""
    return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))


def mask_id_number(id_number: str) -> str:
    """
    身份证号脱敏：中间10位替换为 *
    例如: 320102199001011234 -> 3201**********1234
    """
    if not id_number or len(id_number) < 6:
        return id_number or ''
    return id_number[:4] + '*' * 10 + id_number[14:]


def mask_phone(phone: str) -> str:
    """
    手机号脱敏：中间4位替换为 *
    例如: 13812345678 -> 138****5678
    """
    if not phone or len(phone) < 7:
        return phone or ''
    return phone[:3] + '*' * 4 + phone[7:]
