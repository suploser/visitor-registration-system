// 访客登记系统 - 小程序主入口
App({
  globalData: {
    userInfo: null,
    token: null,
    role: '',           // 'visitor', 'level1', 'level2'
    allRoles: [],       // 所有角色，如 ['level1', 'level2']
    isApprover: false,
    baseUrl: 'http://192.168.253.136:5000',
  },

  onLaunch(options) {
    // 测试环境身份模拟：通过编译模式启动参数指定 mock_openid
    //   mock_openid=v_001      → 访客001
    //   mock_openid=a_l1_001   → 一级审批人001
    //   mock_openid=a_l2_001   → 二级审批人001
    //   mock_openid=reset      → 清除旧身份，随机生成新访客
    // 不传参数 → 使用上次缓存的 openid
    const query = options?.query || {};
    const needRelogin = !!query.mock_openid;
    if (query.mock_openid) {
      if (query.mock_openid === 'reset') {
        this.setMockOpenid('mock_visitor_' + this.randomHex(6));
      } else {
        this.setMockOpenid(query.mock_openid);
      }
    }

    // 有缓存 token 则恢复，否则自动登录
    const token = wx.getStorageSync('token');
    if (token && !needRelogin) {
      this.globalData.token = token;
      this.globalData.role = wx.getStorageSync('role') || '';
      this.globalData.allRoles = JSON.parse(wx.getStorageSync('allRoles') || '[]');
      this.globalData.isApprover = this.globalData.role !== 'visitor';
    } else {
      // 自动登录（mock_openid 变更或首次启动）
      this.login().catch(() => {});
    }
  },

  // 设置/切换 mock openid（仅测试环境有效）
  setMockOpenid(openid) {
    wx.setStorageSync('mock_openid', openid);
    // 清除旧登录态，触发重新登录
    wx.removeStorageSync('token');
    wx.removeStorageSync('role');
    wx.removeStorageSync('allRoles');
    this.globalData.token = null;
    this.globalData.role = '';
    this.globalData.allRoles = [];
    this.globalData.isApprover = false;
  },

  // 获取当前 mock openid
  getMockOpenid() {
    let openid = wx.getStorageSync('mock_openid');
    if (!openid) {
      openid = 'mock_visitor_' + this.randomHex(6);
      wx.setStorageSync('mock_openid', openid);
    }
    return openid;
  },

  randomHex(len) {
    const chars = 'abcdef0123456789';
    let result = '';
    for (let i = 0; i < len; i++) {
      result += chars[Math.floor(Math.random() * chars.length)];
    }
    return result;
  },

  // 获取登录 token
  login() {
    return new Promise((resolve, reject) => {
      wx.login({
        success: (res) => {
          const data = { code: res.code || '' };
          data.mock_openid = this.getMockOpenid();

          wx.request({
            url: `${this.globalData.baseUrl}/api/auth/wechat-login`,
            method: 'POST',
            data: data,
            header: { 'Content-Type': 'application/json' },
            success: (resp) => {
              if (resp.data.code === 0) {
                const { token, role, is_approver, name, department, all_roles } = resp.data.data;
                this.globalData.token = token;
                this.globalData.role = role;
                this.globalData.allRoles = all_roles || [role];
                this.globalData.isApprover = is_approver;
                wx.setStorageSync('token', token);
                wx.setStorageSync('role', role);
                wx.setStorageSync('allRoles', JSON.stringify(all_roles || [role]));
                if (name) wx.setStorageSync('name', name);
                if (department) wx.setStorageSync('department', department);

                // 同步自定义 tabBar 和当前页面状态
                const pages = getCurrentPages();
                if (pages.length > 0) {
                  const page = pages[pages.length - 1];
                  if (typeof page.getTabBar === 'function' && page.getTabBar()) {
                    page.getTabBar().setData({ role: role });
                  }
                  // 刷新首页的 isApprover，避免异步登录导致快捷操作菜单显示错误
                  if (page.setData) {
                    page.setData({ isApprover: is_approver });
                  }
                }
                resolve(resp.data.data);
              } else {
                reject(resp.data);
              }
            },
            fail: reject
          });
        },
        fail: reject
      });
    });
  },

  // 检查登录状态
  checkLogin() {
    if (!this.globalData.token) {
      this.login().catch(err => {
        console.error('Login failed:', err);
      });
      return false;
    }
    return true;
  }
});
