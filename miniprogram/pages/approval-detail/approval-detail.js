// 审批详情页逻辑
const api = require('../../utils/api');
const app = getApp();

Page({
  data: {
    id: 0,
    detail: {},
    comment: '',
    role: '',
    canAct: false,   // 当前用户是否可以审批此申请
  },

  onLoad(options) {
    if (options.id) {
      this.setData({ id: parseInt(options.id), role: app.globalData.role });
      this.loadDetail();
    }
  },

  async loadDetail() {
    try {
      const res = await api.get(`/api/approver/detail/${this.data.id}`);
      if (res.code === 0) {
        const detail = res.data;
        // 格式化车牌号（WXML不支持.join()，须在JS中处理）
        detail.license_plates_text = (detail.license_plates && detail.license_plates.length > 0)
          ? detail.license_plates.join('、') : '';

        // 判断当前用户是否可以审批此申请（双角色兼容）
        const allRoles = app.globalData.allRoles || [app.globalData.role];
        const canAct =
          detail.status === 'pending' ||
          (detail.status === 'level1_approved' && allRoles.includes('level2'));

        this.setData({ detail, canAct });
      }
    } catch (err) {
      console.error('加载详情失败', err);
      wx.showToast({ title: '加载失败', icon: 'none' });
    }
  },

  onCommentInput(e) {
    this.setData({ comment: e.detail.value });
  },

  // 精简后端返回的审批结果消息，使 toast 显示完整
  shortMsg(msg) {
    if (!msg) return '操作成功';
    if (msg.indexOf('审批通过') === 0) return '审批通过';
    if (msg.indexOf('一级审批通过') === 0) return '一级审批通过';
    if (msg.indexOf('已拒绝') === 0) return '已拒绝';
    return msg.length > 14 ? msg.substring(0, 14) + '…' : msg;
  },

  // 审批通过
  async doApprove() {
    wx.showModal({
      title: '确认通过',
      content: '确定通过该访客登记申请吗？',
      success: async (modalRes) => {
        if (modalRes.confirm) {
          try {
            const res = await api.post('/api/approver/approve', {
              visitor_id: this.data.id,
              result: 'approved',
              comment: this.data.comment,
            });
            wx.showToast({ title: this.shortMsg(res.message), icon: 'success' });
            setTimeout(() => wx.navigateBack(), 1500);
          } catch (err) {
            wx.showToast({ title: this.shortMsg(err.message) || '操作失败', icon: 'none' });
          }
        }
      }
    });
  },

  // 拒绝
  async doReject() {
    if (!this.data.comment.trim()) {
      wx.showToast({ title: '拒绝时必须填写审批意见', icon: 'none' });
      return;
    }
    wx.showModal({
      title: '确认拒绝',
      content: '确定拒绝该访客登记申请吗？',
      success: async (modalRes) => {
        if (modalRes.confirm) {
          try {
            const res = await api.post('/api/approver/approve', {
              visitor_id: this.data.id,
              result: 'rejected',
              comment: this.data.comment,
            });
            wx.showToast({ title: this.shortMsg(res.message), icon: 'success' });
            setTimeout(() => wx.navigateBack(), 1500);
          } catch (err) {
            wx.showToast({ title: this.shortMsg(err.message) || '操作失败', icon: 'none' });
          }
        }
      }
    });
  }
});
