// 访客告知书逻辑
const api = require('../../utils/api');

Page({
  data: {
    noticeContent: '',
    agreed: false,
    countdown: 0,
  },

  _timer: null,

  onLoad() {
    this.loadNotice();
  },

  onUnload() {
    this.clearTimer();
  },

  clearTimer() {
    if (this._timer) {
      clearInterval(this._timer);
      this._timer = null;
    }
  },

  async loadNotice() {
    try {
      const res = await api.get('/api/config/public', {}, false);
      if (res.code === 0 && res.data.visitor_notice) {
        this.setData({ noticeContent: res.data.visitor_notice });
      }
    } catch (err) {
      console.error('加载告知书失败', err);
      this.setData({
        noticeContent: '<h3>访客告知书</h3><p>请遵守园区管理规定。</p>'
      });
    }
  },

  toggleAgree() {
    const newAgreed = !this.data.agreed;
    this.setData({ agreed: newAgreed });

    if (newAgreed) {
      // 勾选后启动5秒倒计时
      this.startCountdown();
    } else {
      // 取消勾选则重置倒计时
      this.clearTimer();
      this.setData({ countdown: 0 });
    }
  },

  startCountdown() {
    this.clearTimer();
    this.setData({ countdown: 5 });
    this._timer = setInterval(() => {
      const cd = this.data.countdown - 1;
      if (cd <= 0) {
        this.clearTimer();
        this.setData({ countdown: 0 });
      } else {
        this.setData({ countdown: cd });
      }
    }, 1000);
  },

  goNext() {
    if (!this.data.agreed) {
      wx.showToast({ title: '请先阅读并同意访客告知书', icon: 'none' });
      return;
    }
    if (this.data.countdown > 0) {
      wx.showToast({ title: `请耐心阅读（${this.data.countdown}秒）`, icon: 'none' });
      return;
    }
    wx.navigateTo({ url: '/pages/register/register' });
  }
});
