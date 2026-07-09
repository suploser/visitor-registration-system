"""
数据验证工具
"""
import re
import datetime


def validate_id_number(id_number: str) -> tuple:
    """
    验证中国大陆身份证号码格式
    返回 (is_valid, error_message)
    """
    if not id_number:
        return False, '身份证号码不能为空'

    pattern = r'^\d{17}[\dXx]$'
    if not re.match(pattern, id_number):
        return False, '身份证号码格式不正确（应为18位，末位可为X）'

    # 校验位验证
    weights = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]
    check_codes = '10X98765432'

    total = sum(int(id_number[i]) * weights[i] for i in range(17))
    expected_check = check_codes[total % 11]

    if id_number[17].upper() != expected_check:
        return False, '身份证号码校验位不正确'

    return True, ''


def validate_phone(phone: str) -> tuple:
    """
    验证中国大陆手机号码格式
    返回 (is_valid, error_message)
    """
    if not phone:
        return False, '手机号码不能为空'

    pattern = r'^1[3-9]\d{9}$'
    if not re.match(pattern, phone):
        return False, '手机号码格式不正确（应为11位中国大陆手机号）'

    return True, ''


def validate_license_plate(plate: str) -> tuple:
    """
    验证中国车牌号格式（简化版）
    支持：
    - 普通车牌：京A12345
    - 新能源车牌：京A123456
    返回 (is_valid, error_message)
    """
    if not plate:
        return True, ''  # 车牌号非必填

    # 省份简称
    provinces = '京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤川青藏琼宁'
    # 普通车牌: 省+A-Z+5位数字/字母（不含IO）
    pattern_normal = rf'^[{provinces}][A-HJ-NP-Z][A-HJ-NP-Z0-9]{{5}}$'
    # 新能源车牌: 省+A-Z+6位数字/字母
    pattern_new_energy = rf'^[{provinces}][A-HJ-NP-Z][A-HJ-NP-Z0-9]{{6}}$'

    if re.match(pattern_normal, plate) or re.match(pattern_new_energy, plate):
        return True, ''

    return False, '车牌号格式不正确'


def validate_required(value, field_name: str) -> tuple:
    """验证必填字段"""
    if not value or (isinstance(value, str) and not value.strip()):
        return False, f'{field_name}不能为空'
    return True, ''


def validate_password(password: str) -> tuple:
    """
    验证管理员密码复杂度
    要求：长度>=8，大小写字母+数字+特殊字符至少3种
    返回 (is_valid, error_message)
    """
    if len(password) < 8:
        return False, '密码长度不能少于8位'

    categories = 0
    if re.search(r'[a-z]', password):
        categories += 1
    if re.search(r'[A-Z]', password):
        categories += 1
    if re.search(r'\d', password):
        categories += 1
    if re.search(r'[!@#$%^&*(),.?":{}|<>_\-+=\[\]/\\`~;]', password):
        categories += 1

    if categories < 3:
        return False, '密码需包含大写字母、小写字母、数字、特殊字符中的至少3种'

    return True, ''
