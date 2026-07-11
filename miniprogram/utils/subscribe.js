/**
 * 微信订阅消息工具
 *
 * 封装 wx.requestSubscribeMessage 调用并上报结果到后端。
 *
 * 使用方式：
 *   const subscribe = require('../../utils/subscribe');
 *   // 审批人侧——在待审批列表页 onShow 时调用
 *   subscribe.subscribeApprovalNotices();
 *   // 访客侧——在登记提交成功后调用
 *   subscribe.subscribeResultNotice();
 */
const api = require('./api');

/**
 * 获取后端配置的模板 ID 列表
 * @returns {Promise<Array>} [{template_id, key, name, for_role}, ...]
 */
async function fetchTemplates() {
  try {
    const res = await api.get('/api/notification/templates', {}, false);
    return (res.code === 0 && res.data) ? res.data : [];
  } catch (err) {
    console.error('[Subscribe] 获取模板列表失败', err);
    return [];
  }
}

/**
 * 调起微信订阅消息授权弹窗
 * @param {string[]} tmplIds - 模板 ID 列表
 * @returns {Promise<Object>} 微信返回的授权结果
 */
function requestSubscribe(tmplIds) {
  return new Promise((resolve, reject) => {
    if (!tmplIds || tmplIds.length === 0) {
      resolve({});
      return;
    }

    wx.requestSubscribeMessage({
      tmplIds: tmplIds,
      success(res) {
        console.log('[Subscribe] 授权结果:', res);
        resolve(res);
      },
      fail(err) {
        console.error('[Subscribe] 授权失败:', err);
        // 用户拒绝不视为错误
        if (err.errCode === 20004) {
          resolve({});
        } else {
          resolve({});
        }
      },
    });
  });
}

/**
 * 上报订阅结果到后端
 * @param {Object} wxResult - wx.requestSubscribeMessage 的 success 回调结果
 */
async function reportResult(wxResult) {
  const subscriptions = [];
  // wxResult 的 key 是 template_id，value 是 'accept' / 'reject' / 'ban'
  for (const templateId in wxResult) {
    subscriptions.push({
      template_id: templateId,
      status: wxResult[templateId],
    });
  }

  if (subscriptions.length === 0) return;

  try {
    await api.post('/api/notification/subscribe', { subscriptions });
    console.log('[Subscribe] 订阅结果已上报');
  } catch (err) {
    console.error('[Subscribe] 上报订阅结果失败', err);
  }
}

// ==========================================================================
// 订阅余量查询
// ==========================================================================

/**
 * 查询当前用户的订阅余量（需要登录态）
 * @returns {Promise<Object>} { APPROVAL_NOTICE: {active_count, has_active}, RESULT_NOTICE: {...} }
 */
async function fetchStatus() {
  try {
    const res = await api.get('/api/notification/status');
    if (res.code === 0 && res.data) {
      // 按 key 索引方便查找
      const map = {};
      for (const t of res.data) {
        map[t.key] = t;
      }
      return map;
    }
    return {};
  } catch (err) {
    console.error('[Subscribe] 查询订阅状态失败', err);
    return {};
  }
}

/**
 * 仅在用户没有活跃订阅余量时才弹出授权弹窗。
 * 避免每次操作都骚扰用户。
 */

/**
 * 审批人侧：订阅「待审批通知」—— 余量不足时才弹窗。
 *
 * @returns {Promise<boolean>} 是否成功获得了新的订阅
 */
async function subscribeApprovalNotices() {
  // 先查余量
  const status = await fetchStatus();
  if (status['APPROVAL_NOTICE'] && status['APPROVAL_NOTICE'].active_count > 0) {
    console.log('[Subscribe] 已有 %d 条待审批通知订阅余量，跳过弹窗',
      status['APPROVAL_NOTICE'].active_count);
    return true;
  }

  // 余量不足，弹窗请求新的授权
  const templates = await fetchTemplates();
  const approvalTemplates = templates.filter(
    t => t.for_role && t.for_role.includes('level')
  );

  if (approvalTemplates.length === 0) {
    console.log('[Subscribe] 无审批人相关模板');
    return false;
  }

  const tmplIds = approvalTemplates.map(t => t.template_id);
  const result = await requestSubscribe(tmplIds);
  await reportResult(result);

  return Object.values(result).some(v => v === 'accept');
}

/**
 * 访客侧：订阅「审批结果通知」—— 余量不足时才弹窗。
 *
 * @returns {Promise<boolean>} 是否成功获得了新的订阅
 */
async function subscribeResultNotice() {
  // 先查余量
  const status = await fetchStatus();
  if (status['RESULT_NOTICE'] && status['RESULT_NOTICE'].active_count > 0) {
    console.log('[Subscribe] 已有 %d 条审批结果通知订阅余量，跳过弹窗',
      status['RESULT_NOTICE'].active_count);
    return true;
  }

  // 余量不足，弹窗请求新的授权
  const templates = await fetchTemplates();
  const resultTemplates = templates.filter(
    t => t.key === 'RESULT_NOTICE'
  );

  if (resultTemplates.length === 0) {
    console.log('[Subscribe] 无审批结果通知模板');
    return false;
  }

  const tmplIds = resultTemplates.map(t => t.template_id);
  const result = await requestSubscribe(tmplIds);
  await reportResult(result);

  return Object.values(result).some(v => v === 'accept');
}

/**
 * 智能订阅：根据当前角色自动选择订阅类型。
 * 在 index 页 onShow 或首次进入时调用。
 *
 * @param {string} role - 当前用户角色 ('visitor' | 'level1' | 'level2')
 */
async function smartSubscribe(role) {
  if (role === 'visitor') {
    return subscribeResultNotice();
  } else if (role === 'level1' || role === 'level2') {
    return subscribeApprovalNotices();
  }
  return false;
}

module.exports = {
  fetchTemplates,
  requestSubscribe,
  reportResult,
  subscribeApprovalNotices,
  subscribeResultNotice,
  smartSubscribe,
};
