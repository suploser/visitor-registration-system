"""
微信小程序订阅消息 API 封装

使用文档: https://developers.weixin.qq.com/miniprogram/dev/OpenApiDoc/mp-message-management/subscribe-message/sendMessage.html
"""
import os
import time
import logging
import requests

logger = logging.getLogger(__name__)


class WxSubscribeClient:
    """微信订阅消息发送客户端

    所有方法内部静默捕获异常 —— 消息发送失败不应影响审批主流程。
    """

    # 微信 API 端点
    TOKEN_URL = 'https://api.weixin.qq.com/cgi-bin/token'
    SEND_URL = 'https://api.weixin.qq.com/cgi-bin/message/subscribe/send'

    def __init__(self, appid=None, secret=None):
        self._appid = appid or os.environ.get('WECHAT_APPID', '')
        self._secret = secret or os.environ.get('WECHAT_SECRET', '')
        self._access_token = None
        self._token_expires_at = 0

    # ------------------------------------------------------------------
    # Access Token
    # ------------------------------------------------------------------

    def get_access_token(self):
        """获取并缓存 access_token（提前 5 分钟刷新）"""
        now = time.time()
        if self._access_token and now < self._token_expires_at - 300:
            return self._access_token

        if not self._appid or not self._secret:
            logger.warning('[WxSubscribe] WECHAT_APPID / WECHAT_SECRET 未配置，无法获取 access_token')
            return None

        try:
            resp = requests.get(self.TOKEN_URL, params={
                'grant_type': 'client_credential',
                'appid': self._appid,
                'secret': self._secret,
            }, timeout=10)
            data = resp.json()
            if 'access_token' in data:
                self._access_token = data['access_token']
                self._token_expires_at = now + data.get('expires_in', 7200)
                logger.info('[WxSubscribe] access_token 获取成功，有效期 %s 秒', data.get('expires_in'))
                return self._access_token
            else:
                logger.error('[WxSubscribe] 获取 access_token 失败: %s', data)
                return None
        except Exception as e:
            logger.error('[WxSubscribe] 获取 access_token 异常: %s', e)
            return None

    # ------------------------------------------------------------------
    # 发送消息（底层）
    # ------------------------------------------------------------------

    def send(self, openid, template_id, data, page=''):
        """
        发送订阅消息

        Args:
            openid: 接收者 openid
            template_id: 模板 ID
            data: 模板数据 dict，格式为 {key: {value: 'xxx'}}
            page: 点击消息跳转的小程序页面路径（可选）

        Returns:
            bool: 是否发送成功
        """
        access_token = self.get_access_token()
        if not access_token:
            return False

        payload = {
            'touser': openid,
            'template_id': template_id,
            'page': page or '',
            'data': data,
            'miniprogram_state': 'formal',  # 正式版
        }

        try:
            resp = requests.post(
                f'{self.SEND_URL}?access_token={access_token}',
                json=payload,
                timeout=10,
            )
            result = resp.json()
            if result.get('errcode') == 0:
                logger.info('[WxSubscribe] 消息发送成功: openid=%s, template=%s', openid, template_id)
                return True
            else:
                logger.error('[WxSubscribe] 消息发送失败: %s', result)
                return False
        except Exception as e:
            logger.error('[WxSubscribe] 消息发送异常: %s', e)
            return False

    # ------------------------------------------------------------------
    # 业务消息封装
    # ------------------------------------------------------------------

    def send_approval_notice(self, openid, visitor_name, department, visitor_id):
        """
        发送「待审批通知」给审批人

        模板字段（需与微信后台模板一致）:
          - thing1: 访客姓名
          - thing2: 访问部门
          - time3: 提交时间
        """
        from datetime import datetime

        template_id = os.environ.get('WX_TMPL_APPROVAL_NOTICE', '')
        if not template_id:
            logger.warning('[WxSubscribe] WX_TMPL_APPROVAL_NOTICE 未配置')
            return False

        data = {
            'thing1': {'value': visitor_name[:20]},       # 限制 20 字符
            'thing2': {'value': department[:20]},
            'time3': {'value': datetime.now().strftime('%Y-%m-%d %H:%M')},
        }
        page = f'pages/approval-detail/approval-detail?id={visitor_id}'

        return self.send(openid, template_id, data, page)

    def send_result_notice(self, openid, visitor_name, status, reason=''):
        """
        发送「审批结果通知」给访客

        模板字段（需与微信后台模板一致）:
          - thing1: 访客姓名
          - phrase2: 审批结果
          - thing3: 备注
        """
        template_id = os.environ.get('WX_TMPL_RESULT_NOTICE', '')
        if not template_id:
            logger.warning('[WxSubscribe] WX_TMPL_RESULT_NOTICE 未配置')
            return False

        status_map = {
            'approved': '审批通过',
            'rejected': '审批未通过',
        }
        result_text = status_map.get(status, status)

        data = {
            'thing1': {'value': visitor_name[:20]},
            'phrase2': {'value': result_text},
            'thing3': {'value': (reason or '请查看详情')[:20]},
        }
        page = 'pages/result/result'

        return self.send(openid, template_id, data, page)


# 全局单例
_client_instance = None


def get_wx_client():
    """获取 WxSubscribeClient 单例"""
    global _client_instance
    if _client_instance is None:
        _client_instance = WxSubscribeClient()
    return _client_instance
