// 自定义 TabBar - 根据角色动态切换菜单
const app = getApp();

Component({
  data: {
    role: '',
    selected: 0,
    visitorTabs: [
      { pagePath: '/pages/index/index', text: '首页', icon: 'home' },
      { pagePath: '/pages/result/result', text: '我的', icon: 'profile' },
    ],
    approverTabs: [
      { pagePath: '/pages/index/index', text: '首页', icon: 'home' },
      { pagePath: '/pages/approval-list/approval-list', text: '待审批', icon: 'pending' },
      { pagePath: '/pages/approval-history/approval-history', text: '审批记录', icon: 'history' },
    ],
  },

  lifetimes: {
    attached() {
      this.setData({ role: app.globalData.role || 'visitor' });
    },
  },

  methods: {
    switchTab(e) {
      const { path, index } = e.currentTarget.dataset;
      wx.switchTab({ url: path });
      this.setData({ selected: index });
    },
  },
});
