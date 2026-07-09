// 审批结果页逻辑
const api = require('../../utils/api');
const app = getApp();

Page({
  data: {
    role: 'visitor',
    hasRecord: false,
    status: '',
    visitor: {},
    credential: {},
  },

  onShow() {
    this.setData({ role: app.globalData.role || 'visitor' });
    // 同步自定义 tabBar
    if (typeof this.getTabBar === 'function' && this.getTabBar()) {
      this.getTabBar().setData({ selected: 1, role: app.globalData.role || 'visitor' });
    }
    if (app.globalData.role === 'visitor') {
      this.loadStatus();
    }
  },

  async loadStatus() {
    try {
      const res = await api.get('/api/visitor/status');
      if (res.code === 0 && res.data.has_record) {
        this.setData({
          hasRecord: true,
          status: res.data.visitor.status,
          visitor: res.data.visitor,
        });

        // 如果已通过，获取凭证
        if (res.data.visitor.status === 'approved') {
          this.loadCredential();
        }
      } else {
        this.setData({ hasRecord: false, status: '' });
      }
    } catch (err) {
      console.error('加载状态失败', err);
    }
  },

  async loadCredential() {
    try {
      const res = await api.get('/api/visitor/credential');
      if (res.code === 0) {
        this.setData({ credential: res.data });
      }
    } catch (err) {
      console.error('加载凭证失败', err);
    }
  },

  goToRegister() {
    wx.navigateTo({ url: '/pages/notice/notice' });
  },

  goToApprovalList() {
    wx.switchTab({ url: '/pages/approval-list/approval-list' });
  },

  onPullDownRefresh() {
    this.loadStatus();
    wx.stopPullDownRefresh();
  }
});
