// 首页逻辑
const api = require('../../utils/api');
const app = getApp();

// 小程序本地默认图片
const DEFAULT_BG = '/images/hero-bg.png';
const DEFAULT_SCROLL_IMAGES = [
  '/images/company-1.png',
  '/images/company-2.png',
  '/images/company-3.png',
];

Page({
  data: {
    bgImage: DEFAULT_BG,
    bgImageError: false,
    scrollImages: [],
    displayScrollImages: [],
    showWelcome: false,
    welcomeMessage: '',
    isApprover: false,
  },

  onLoad() {
    this.loadConfig();
  },

  onShow() {
    this.syncTabBar(0);
    // onLaunch 异步登录后角色可能变化，每次显示都刷新
    this.setData({ isApprover: app.globalData.isApprover });
    const visited = wx.getStorageSync('welcome_shown');
    if (!visited) {
      this.setData({ showWelcome: true });
    }
  },

  syncTabBar(idx) {
    if (typeof this.getTabBar === 'function' && this.getTabBar()) {
      this.getTabBar().setData({ selected: idx, role: app.globalData.role || 'visitor' });
    }
  },

  // 加载系统配置
  async loadConfig() {
    try {
      const res = await api.get('/api/config/public', {}, false);
      if (res.code === 0) {
        const data = res.data;

        // 背景图
        const bgImages = this.parseImages(data.home_bg_images);
        if (bgImages.length > 0) {
          this.setData({ bgImage: bgImages[0], bgImageError: false });
        }

        // 滚动图片
        const scrollImages = this.parseImages(data.company_scroll_images);
        if (scrollImages.length === 0) {
          // 使用默认图片
          this.setData({
            displayScrollImages: DEFAULT_SCROLL_IMAGES,
          });
        } else {
          this.setData({
            displayScrollImages: scrollImages,
          });
        }

        this.setData({
          welcomeMessage: data.welcome_message || '欢迎使用访客登记系统',
        });
      }
    } catch (err) {
      console.error('加载配置失败，使用默认图片', err);
      // 加载失败时使用默认图片
      this.setData({
        displayScrollImages: DEFAULT_SCROLL_IMAGES,
      });
    }
  },

  // 解析图片JSON
  parseImages(jsonStr) {
    try {
      if (typeof jsonStr === 'string') {
        const parsed = JSON.parse(jsonStr);
        return Array.isArray(parsed) ? parsed : [];
      }
      if (Array.isArray(jsonStr)) {
        return jsonStr;
      }
    } catch (e) {
      console.error('图片配置解析失败', e);
    }
    return [];
  },

  // 背景图加载失败，使用CSS渐变
  onBgImageError() {
    this.setData({ bgImageError: true, bgImage: '' });
  },

  // 滚动图片加载失败，移除该项
  onScrollImageError(e) {
    const index = e.currentTarget.dataset.index;
    const images = this.data.displayScrollImages;
    images[index] = '';  // 清空失败项
    this.setData({ displayScrollImages: images.filter(Boolean) });
  },

  // 关闭欢迎弹窗
  closeWelcome() {
    wx.setStorageSync('welcome_shown', true);
    this.setData({ showWelcome: false });
  },

  preventMove() {},

  goToRegister() {
    if (!app.checkLogin()) return;
    wx.navigateTo({ url: '/pages/notice/notice' });
  },

  goToResult() {
    if (!app.checkLogin()) return;
    wx.switchTab({ url: '/pages/result/result' });
  },

  goToApprovalList() {
    if (!app.checkLogin()) return;
    wx.switchTab({ url: '/pages/approval-list/approval-list' });
  },

  goToApprovalHistory() {
    if (!app.checkLogin()) return;
    wx.switchTab({ url: '/pages/approval-history/approval-history' });
  },

  onShareAppMessage() {
    return {
      title: '访客登记系统',
      path: '/pages/index/index',
    };
  }
});
