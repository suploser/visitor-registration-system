// 常量定义

// 省份列表（用于车牌号输入）
const PROVINCES = [
  { name: '京', full: '北京市' },
  { name: '津', full: '天津市' },
  { name: '沪', full: '上海市' },
  { name: '渝', full: '重庆市' },
  { name: '冀', full: '河北省' },
  { name: '豫', full: '河南省' },
  { name: '云', full: '云南省' },
  { name: '辽', full: '辽宁省' },
  { name: '黑', full: '黑龙江省' },
  { name: '湘', full: '湖南省' },
  { name: '皖', full: '安徽省' },
  { name: '鲁', full: '山东省' },
  { name: '新', full: '新疆维吾尔自治区' },
  { name: '苏', full: '江苏省' },
  { name: '浙', full: '浙江省' },
  { name: '赣', full: '江西省' },
  { name: '鄂', full: '湖北省' },
  { name: '桂', full: '广西壮族自治区' },
  { name: '甘', full: '甘肃省' },
  { name: '晋', full: '山西省' },
  { name: '蒙', full: '内蒙古自治区' },
  { name: '陕', full: '陕西省' },
  { name: '吉', full: '吉林省' },
  { name: '闽', full: '福建省' },
  { name: '贵', full: '贵州省' },
  { name: '粤', full: '广东省' },
  { name: '川', full: '四川省' },
  { name: '青', full: '青海省' },
  { name: '藏', full: '西藏自治区' },
  { name: '琼', full: '海南省' },
  { name: '宁', full: '宁夏回族自治区' },
];

// 新能源车牌字母标识（第3位）
const NEW_ENERGY_LETTERS = ['D', 'F', 'G', 'H', 'J', 'K', 'L', 'M', 'N'];

// 访问目的选项
const VISIT_PURPOSES = [
  '商务洽谈',
  '技术交流',
  '参观考察',
  '会议参加',
  '培训学习',
  '面试',
  '送货',
  '维修',
  '其他',
];

module.exports = {
  PROVINCES,
  NEW_ENERGY_LETTERS,
  VISIT_PURPOSES,
};
