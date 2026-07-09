// 审批人信息录入页
const api = require('../../utils/api');
const app = getApp();

Page({
  data: {
    token: '',
    role: '',
    roleLabel: '',
    departmentOptions: [],
    loading: true,
    errorMsg: '',
    // 验证码相关
    verified: false,
    verifyCode: '',
    verifying: false,
    // 授权相关
    authorized: false,
    success: false,
    successMsg: '',
    form: {
      name: '',
      department: '',
    },
    submitting: false,
  },

  onLoad(options) {
    const token = options.token || '';
    if (!token) {
      this.setData({ loading: false, errorMsg: '缺少注册凭证，请联系管理员重新生成链接' });
      return;
    }
    this.setData({ token });
    this.checkToken();
  },

  // 验证 token 有效性（不传验证码，仅做token格式校验）
  async checkToken() {
    try {
      const res = await api.get(`/api/approver/register/${this.data.token}`, {}, false);
      // code=1 + need_verify：token有效，但需要输入验证码
      if (res.code === 1 && res.need_verify) {
        const role = res.role || '';
        this.setData({
          loading: false,
          role: role,
          roleLabel: role === 'level1' ? '一级审批人' : (role === 'level2' ? '二级审批人' : ''),
        });
        return;
      }
      if (res.code === 0) {
        this.setData({
          loading: false,
          role: res.data.role,
          departmentOptions: res.data.department_options || [],
          verified: true,
        });
      } else {
        this.setData({ loading: false, errorMsg: res.message || '链接无效' });
      }
    } catch (err) {
      this.setData({ loading: false, errorMsg: err.message || '链接验证失败' });
    }
  },

  // 验证码输入
  onCodeInput(e) {
    this.setData({ verifyCode: e.detail.value });
  },

  // 提交验证码
  async verifyCode() {
    const code = this.data.verifyCode.trim();
    if (!code || code.length !== 6) {
      wx.showToast({ title: '请输入6位验证码', icon: 'none' });
      return;
    }

    this.setData({ verifying: true });
    try {
      const res = await api.get(
        `/api/approver/register/${this.data.token}?code=${code}`,
        {},
        false
      );
      if (res.code === 0) {
        this.setData({
          verified: true,
          role: res.data.role,
          roleLabel: res.data.role === 'level1' ? '一级审批人' : '二级审批人',
          departmentOptions: res.data.department_options || [],
        });
        wx.showToast({ title: '验证通过', icon: 'success' });
      } else {
        wx.showToast({ title: res.message || '验证失败', icon: 'none' });
      }
    } catch (err) {
      wx.showToast({ title: err.message || '验证失败', icon: 'none' });
    } finally {
      this.setData({ verifying: false });
    }
  },

  // 微信授权
  async doAuth() {
    try {
      await app.login();
      this.setData({ authorized: true });
      wx.showToast({ title: '授权成功', icon: 'success' });
    } catch (err) {
      wx.showToast({ title: '授权失败，请重试', icon: 'none' });
    }
  },

  onInput(e) {
    const field = e.currentTarget.dataset.field;
    this.setData({ [`form.${field}`]: e.detail.value });
  },

  onDeptChange(e) {
    const idx = e.detail.value;
    const dept = this.data.departmentOptions[idx];
    this.setData({ 'form.department': dept ? dept.value : '' });
  },

  // 提交注册
  async submitRegister() {
    const { form, verifyCode } = this.data;
    if (!form.name.trim()) {
      wx.showToast({ title: '请输入姓名', icon: 'none' });
      return;
    }
    if (!form.department) {
      wx.showToast({ title: '请选择部门', icon: 'none' });
      return;
    }

    this.setData({ submitting: true });
    try {
      const res = await api.post(`/api/approver/register/${this.data.token}`, {
        name: form.name.trim(),
        department: form.department,
        code: verifyCode.trim(),
      });
      if (res.code === 0) {
        this.setData({
          success: true,
          successMsg: res.message || `注册成功！您已成为${this.data.role === 'level1' ? '一级' : '二级'}审批人`,
        });
      } else {
        wx.showToast({ title: res.message || '提交失败', icon: 'none' });
      }
    } catch (err) {
      wx.showToast({ title: err.message || '提交失败', icon: 'none' });
    } finally {
      this.setData({ submitting: false });
    }
  },

  goHome() {
    wx.reLaunch({ url: '/pages/index/index' });
  },
});
