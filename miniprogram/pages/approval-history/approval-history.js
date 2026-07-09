// 审批记录页逻辑
const api = require('../../utils/api');
const app = getApp();

Page({
  data: {
    records: [],
    loading: false,
  },

  onShow() {
    if (typeof this.getTabBar === 'function' && this.getTabBar()) {
      this.getTabBar().setData({ selected: 2, role: app.globalData.role || 'visitor' });
    }
    this.loadHistory();
  },

  async loadHistory() {
    this.setData({ loading: true });
    try {
      const res = await api.get('/api/approver/history');
      if (res.code === 0) {
        this.setData({ records: res.data });
      }
    } catch (err) {
      console.error('加载审批记录失败', err);
    } finally {
      this.setData({ loading: false });
    }
  },

  onPullDownRefresh() {
    this.loadHistory().then(() => wx.stopPullDownRefresh());
  }
});
