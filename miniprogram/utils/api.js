// API 请求封装
const app = getApp();

/**
 * 发送请求
 */
function request(url, method = 'GET', data = {}, needAuth = true) {
  return new Promise((resolve, reject) => {
    const header = {
      'Content-Type': 'application/json',
    };

    if (needAuth) {
      const token = wx.getStorageSync('token');
      if (token) {
        header['Authorization'] = `Bearer ${token}`;
      }
    }

    wx.request({
      url: `${app.globalData.baseUrl}${url}`,
      method,
      data,
      header,
      success(res) {
        if (res.statusCode === 401) {
          // 登录过期，清除缓存
          wx.removeStorageSync('token');
          wx.removeStorageSync('role');
          wx.showModal({
            title: '提示',
            content: '登录已过期，请重新进入小程序',
            showCancel: false,
            success: () => {
              app.login();
            }
          });
          reject(res.data);
        } else if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data);
        } else {
          reject(res.data);
        }
      },
      fail(err) {
        wx.showToast({
          title: '网络请求失败',
          icon: 'none',
          duration: 2000,
        });
        reject(err);
      }
    });
  });
}

// GET 请求
function get(url, data = {}, needAuth = true) {
  // 将data转为query string
  const queryArr = [];
  for (const key in data) {
    if (data[key] !== undefined && data[key] !== null && data[key] !== '') {
      queryArr.push(`${encodeURIComponent(key)}=${encodeURIComponent(data[key])}`);
    }
  }
  const queryStr = queryArr.join('&');
  const fullUrl = queryStr ? `${url}?${queryStr}` : url;
  return request(fullUrl, 'GET', {}, needAuth);
}

// POST 请求
function post(url, data = {}, needAuth = true) {
  return request(url, 'POST', data, needAuth);
}

// PUT 请求
function put(url, data = {}, needAuth = true) {
  return request(url, 'PUT', data, needAuth);
}

// DELETE 请求
function del(url, data = {}, needAuth = true) {
  return request(url, 'DELETE', data, needAuth);
}

module.exports = {
  request,
  get,
  post,
  put,
  del,
};
