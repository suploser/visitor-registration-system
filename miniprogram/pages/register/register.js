// 访客登记页逻辑
const api = require('../../utils/api');
const constants = require('../../utils/constants');
const subscribe = require('../../utils/subscribe');

Page({
  data: {
    departments: [],
    visitPurposes: constants.VISIT_PURPOSES,
    dateTimeRange: [[], [], [], [], []],  // [年, 月, 日, 时, 分]
    dateTimeIndex: [0, 0, 0, 0, 0],
    form: {
      name: '',
      phone: '',
      id_number: '',
      host_name: '',
      host_department: '',
      visit_start: '',
      visit_end: '',
      visit_location: '',
      visit_purpose: '',
      visitor_count: 1,
      has_device: false,
      device_info: '',
      license_plates: [],
      companions: [],
    },
    submitting: false,
  },

  onLoad() {
    this.loadDepartments();
    this.initDateTimeRange();
    this.checkAndAddCompanions();
  },

  // 加载部门列表
  async loadDepartments() {
    try {
      const res = await api.get('/api/visitor/departments');
      if (res.code === 0) {
        this.setData({ departments: res.data });
      }
    } catch (err) {
      console.error('加载部门失败', err);
    }
  },

  // 初始化日期时间选择器
  initDateTimeRange() {
    const now = new Date();
    const currentYear = now.getFullYear();
    const years = [];
    const months = [];
    const days = [];
    const hours = [];
    const minutes = [];

    for (let i = currentYear; i <= currentYear + 1; i++) years.push(`${i}年`);
    for (let i = 1; i <= 12; i++) months.push(`${i}月`);
    for (let i = 1; i <= 31; i++) days.push(`${i}日`);
    for (let i = 0; i <= 23; i++) hours.push(`${String(i).padStart(2, '0')}时`);
    for (let i = 0; i <= 59; i += 5) minutes.push(`${String(i).padStart(2, '0')}分`);

    this.setData({
      dateTimeRange: [years, months, days, hours, minutes],
    });
  },

  // 日期时间列变化
  onDateTimeColumnChange(e) {
    // 处理列的联动（年月日的变化）
    const { column, value } = e.detail;
    const dateTimeIndex = this.data.dateTimeIndex;
    dateTimeIndex[column] = value;
    this.setData({ dateTimeIndex });
  },

  // 开始时间选择
  onStartTimeChange(e) {
    const values = e.detail.value;
    const dt = this.parseDateTime(values);
    if (dt) {
      this.setData({ 'form.visit_start': dt });
    }
  },

  // 结束时间选择
  onEndTimeChange(e) {
    const values = e.detail.value;
    const dt = this.parseDateTime(values);
    if (dt) {
      this.setData({ 'form.visit_end': dt });
    }
  },

  // 解析日期时间
  parseDateTime(values) {
    const ranges = this.data.dateTimeRange;
    if (!ranges[0].length || !values || values.length < 5) return null;

    const year = parseInt(ranges[0][values[0]]);
    const month = parseInt(ranges[1][values[1]]);
    const day = parseInt(ranges[2][values[2]]);
    const hour = parseInt(ranges[3][values[3]]);
    const minute = parseInt(ranges[4][values[4]]);

    const m = String(month).padStart(2, '0');
    const d = String(day).padStart(2, '0');
    const h = String(hour).padStart(2, '0');
    const min = String(minute).padStart(2, '0');
    return `${year}-${m}-${d} ${h}:${min}`;
  },

  // 通用输入事件
  onInput(e) {
    const field = e.currentTarget.dataset.field;
    const value = e.detail.value;
    this.setData({ [`form.${field}`]: value });
    // 来访人数变更时同步同行人输入框
    if (field === 'visitor_count') {
      this.checkAndAddCompanions();
    }
  },

  // 部门选择
  onDeptChange(e) {
    const dept = this.data.departments[e.detail.value];
    this.setData({ 'form.host_department': dept ? dept.name : '' });
  },

  // 访问目的选择
  onPurposeChange(e) {
    this.setData({ 'form.visit_purpose': this.data.visitPurposes[e.detail.value] });
  },

  // 信息设备开关
  onSwitchDevice(e) {
    this.setData({ 'form.has_device': e.detail.value });
    if (!e.detail.value) {
      this.setData({ 'form.device_info': '' });
    }
  },

  // 车牌号变更
  onPlateChange(e) {
    this.setData({ 'form.license_plates': e.detail.license_plates || [] });
  },

  // 检查并同步同行人输入框数量
  checkAndAddCompanions() {
    const count = parseInt(this.data.form.visitor_count) || 1;
    const expected = Math.max(0, count - 1);
    let companions = this.data.form.companions;
    const currentLen = companions.length;
    if (expected > currentLen) {
      // 人数增加 → 追加空槽位
      for (let i = 0; i < expected - currentLen; i++) {
        companions.push({ name: '', id_number: '' });
      }
    } else if (expected < currentLen) {
      // 人数减少 → 截掉多余槽位
      companions = companions.slice(0, expected);
    }
    this.setData({ 'form.companions': companions });
  },

  // 添加同行人
  addCompanion() {
    const companions = this.data.form.companions;
    companions.push({ name: '', id_number: '' });
    this.setData({ 'form.companions': companions });
  },

  // 删除同行人
  removeCompanion(e) {
    const index = e.currentTarget.dataset.index;
    const companions = this.data.form.companions;
    companions.splice(index, 1);
    this.setData({ 'form.companions': companions });
  },

  // 同行人输入
  onCompanionInput(e) {
    const { index, field } = e.currentTarget.dataset;
    this.setData({ [`form.companions[${index}].${field}`]: e.detail.value });
  },

  // 表单验证
  validateForm() {
    const f = this.data.form;
    if (!f.name.trim()) return '请输入访客姓名';
    if (!f.phone || f.phone.length !== 11) return '请输入正确的11位手机号';
    if (!f.id_number || f.id_number.length !== 18) return '请输入正确的18位身份证号';
    if (!f.host_name.trim()) return '请输入接待人姓名';
    if (!f.host_department) return '请选择接待人部门';
    if (!f.visit_start) return '请选择访问开始时间';
    if (!f.visit_end) return '请选择访问结束时间';
    if (f.visit_end <= f.visit_start) return '访问结束时间必须晚于开始时间';
    if (!f.visit_location.trim()) return '请输入访问地点';
    if (!f.visit_purpose) return '请选择访问目的';
    if (f.has_device && !f.device_info.trim()) return '请输入信息设备名称型号';

    // 验证同行人：数量必须与来访人数匹配
    const count = parseInt(f.visitor_count) || 1;
    const expected = Math.max(0, count - 1);
    // 过滤有效填写的同行人
    const filledCompanions = f.companions.filter(c => c.name.trim() || (c.id_number && c.id_number.trim()));
    if (filledCompanions.length !== expected) {
      return `来访人数为${count}人，请完整填写${expected}位同行人信息`;
    }
    for (let i = 0; i < f.companions.length; i++) {
      const c = f.companions[i];
      if (!c.name.trim()) return `请输入同行人${i + 1}的姓名`;
      if (!c.id_number || c.id_number.length !== 18) return `请输入同行人${i + 1}正确的18位身份证号`;
    }
    return null;
  },

  // 提交表单
  async submitForm() {
    const error = this.validateForm();
    if (error) {
      wx.showToast({ title: error, icon: 'none', duration: 2500 });
      return;
    }

    this.setData({ submitting: true });

    try {
      // 构建提交数据，确保类型正确
      const formData = {
        ...this.data.form,
        visitor_count: parseInt(this.data.form.visitor_count) || 1,
        // 仅发送有效填写的同行人
        companions: this.data.form.companions
          .filter(c => c.name.trim() && c.id_number.trim())
          .map(c => ({ name: c.name.trim(), id_number: c.id_number.trim() })),
      };
      const res = await api.post('/api/visitor/register', formData);
      if (res.code === 0) {
        // 提交成功后尝试获取订阅消息授权（余量充足时不弹窗）
        subscribe.subscribeResultNotice();
        wx.showModal({
          title: '提交成功',
          content: '您的访客登记申请已提交，请等待审批。',
          showCancel: false,
          success: () => {
            wx.switchTab({ url: '/pages/result/result' });
          }
        });
      } else {
        wx.showToast({ title: res.message || '提交失败', icon: 'none' });
      }
    } catch (err) {
      wx.showToast({ title: err.message || '网络错误', icon: 'none' });
    } finally {
      this.setData({ submitting: false });
    }
  }
});
