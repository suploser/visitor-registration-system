// 待审批列表逻辑
const api = require('../../utils/api');
const app = getApp();

Page({
  data: {
    list: [],
    loading: false,
    roleText: '',
  },

  onLoad() {
    const allRoles = app.globalData.allRoles || [];
    if (allRoles.length >= 2) {
      this.setData({ roleText: '一级/二级审批人' });
    } else if (allRoles[0] === 'level1' || app.globalData.role === 'level1') {
      this.setData({ roleText: '一级审批人' });
    } else if (allRoles[0] === 'level2' || app.globalData.role === 'level2') {
      this.setData({ roleText: '二级审批人' });
    }
  },

  onShow() {
    if (typeof this.getTabBar === 'function' && this.getTabBar()) {
      this.getTabBar().setData({ selected: 1, role: app.globalData.role || 'visitor' });
    }
    this.loadList();
  },

  async loadList() {
    this.setData({ loading: true });
    try {
      const res = await api.get('/api/approver/pending');
      if (res.code === 0) {
        // 格式化车牌号（WXML不支持.join()，须在JS中处理）
        const list = (res.data || []).map(item => ({
          ...item,
          license_plates_text: (item.license_plates && item.license_plates.length > 0)
            ? item.license_plates.join('、') : '',
        }));
        this.setData({ list });
      }
    } catch (err) {
      console.error('加载待审批列表失败', err);
      if (err.code === 403) {
        wx.showToast({ title: '您没有审批权限', icon: 'none' });
      }
    } finally {
      this.setData({ loading: false });
    }
  },

  goToDetail(e) {
    const id = e.currentTarget.dataset.id;
    wx.navigateTo({ url: `/pages/approval-detail/approval-detail?id=${id}` });
  },

  onPullDownRefresh() {
    this.loadList().then(() => wx.stopPullDownRefresh());
  }
});
