"""
通知引擎 —— 通过 SQLAlchemy 事件监听 Visitor 状态变更，
在审批流程关键节点触发微信订阅消息推送。

核心约束:
  - 仅生产环境 (DEBUG=False) 启用
  - 所有通知逻辑不抛异常，保证审批主流程不受影响
  - 不对现有业务代码做任何修改，纯旁路监听
"""
import logging
from datetime import datetime
from sqlalchemy import event, inspect as sa_inspect

from models import db
from models.visitor import Visitor
from models.approver import Approver
from models.notification import NotificationSubscription
from services.approval import ApprovalService
from services.wx_subscribe import get_wx_client

logger = logging.getLogger(__name__)


def init_notification(app):
    """
    初始化通知系统。
    仅在 DEBUG=False 时注册 SQLAlchemy 事件监听器。

    在 app.py 中调用:
        from services.notification import init_notification
        init_notification(app)
    """
    if app.config.get('DEBUG', True):
        logger.info('[Notification] 测试环境，通知系统未启用')
        return

    logger.info('[Notification] 生产环境，注册通知事件监听器')

    # 注册事件监听
    event.listen(Visitor, 'after_insert', _on_visitor_created)
    event.listen(Visitor, 'after_update', _on_visitor_updated)

    logger.info('[Notification] 事件监听器注册完成')


# ------------------------------------------------------------------
# 事件处理器
# ------------------------------------------------------------------

def _on_visitor_created(mapper, connection, target):
    """Visitor 新插入时触发——仅处理：新提交的 pending 登记"""
    _safe_notify(target, is_new=True)


def _on_visitor_updated(mapper, connection, target):
    """Visitor 更新时触发——检测 status 字段变更"""
    insp = sa_inspect(target)
    status_history = insp.attrs.status.history

    if not status_history.has_changes():
        return

    old_status = status_history.deleted[0] if status_history.deleted else None
    new_status = status_history.added[0] if status_history.added else None

    if old_status == new_status:
        return

    logger.info('[Notification] 访客 %s (id=%s) 状态变更: %s → %s',
                target.name, target.id, old_status, new_status)

    _handle_status_transition(target, old_status, new_status)


# ------------------------------------------------------------------
# 状态转换 → 通知分发
# ------------------------------------------------------------------

def _handle_status_transition(visitor, old_status, new_status):
    """根据状态转换决定通知谁"""
    # 1. 访客提交/重新提交 → 通知一级审批人
    #    - None → pending（新建）—— 由 _on_visitor_created 处理
    #    - rejected → pending（重新提交）
    if new_status == 'pending':
        if old_status is None or old_status == 'rejected':
            _notify_level1_approvers(visitor)
        return

    # 2. 一级审批通过 → 通知二级审批人
    if new_status == 'level1_approved':
        _notify_level2_approvers(visitor)
        return

    # 3. 审批终结（通过/拒绝）→ 通知访客
    if new_status in ('approved', 'rejected'):
        _notify_visitor(visitor, new_status)
        return


def _safe_notify(visitor, is_new=False):
    """安全触发通知入口"""
    try:
        if is_new:
            status = visitor.status or 'pending'
            # 对于新建记录，如果当前 status 已经是 level1_approved（跳过了 L1）
            # 则直接通知 L2；否则通知 L1
            if status == 'level1_approved':
                logger.info('[Notification] 新建访客跳过一级（无L1或L1即L2），通知二级审批人')
                _notify_level2_approvers(visitor)
            elif status == 'pending':
                _notify_level1_approvers(visitor)
    except Exception:
        logger.exception('[Notification] _safe_notify 异常，已忽略')


# ------------------------------------------------------------------
# 通知实现
# ------------------------------------------------------------------

def _notify_level1_approvers(visitor):
    """通知接待部门的所有一级审批人"""
    try:
        level1_approvers = Approver.query.filter(
            Approver.department == visitor.host_department,
            Approver.role == 'level1',
            Approver.is_registered == True,
        ).all()

        if not level1_approvers:
            logger.info('[Notification] 部门 "%s" 无一级审批人，跳过通知', visitor.host_department)
            return

        client = get_wx_client()
        for approver in level1_approvers:
            if not approver.openid:
                continue
            # 检查是否有可用订阅
            tmpl_id = _get_template_id('APPROVAL_NOTICE')
            if not tmpl_id:
                continue
            sub = NotificationSubscription.query.filter(
                NotificationSubscription.openid == approver.openid,
                NotificationSubscription.template_id == tmpl_id,
                NotificationSubscription.status == 'active',
            ).first()
            if not sub:
                logger.info('[Notification] 审批人 %s 无可用订阅，跳过', approver.openid)
                continue

            ok = client.send_approval_notice(
                openid=approver.openid,
                visitor_name=visitor.name,
                department=visitor.host_department,
                visitor_id=visitor.id,
            )
            if ok:
                sub.status = 'used'
                sub.used_at = datetime.utcnow()
                logger.info('[Notification] 一级审批通知已发送: %s → %s', visitor.name, approver.name)
    except Exception:
        logger.exception('[Notification] 通知一级审批人异常，已忽略')


def _notify_level2_approvers(visitor):
    """通知所有二级审批人"""
    try:
        level2_approvers = ApprovalService.get_all_level2_approvers()

        if not level2_approvers:
            logger.info('[Notification] 无二级审批人，跳过通知')
            return

        client = get_wx_client()
        for approver in level2_approvers:
            if not approver.openid:
                continue

            # 跳过刚作为 L1 审批了本条记录的 L2（避免冗余通知）
            # 通过遍历 session 中待提交的 ApprovalRecord 精确判断
            if _was_l1_approver(visitor.id, approver.id):
                logger.info('[Notification] 二级审批人 %s 刚作为一级审批人处理过此申请，跳过',
                            approver.name)
                continue

            tmpl_id = _get_template_id('APPROVAL_NOTICE')
            if not tmpl_id:
                continue
            sub = NotificationSubscription.query.filter(
                NotificationSubscription.openid == approver.openid,
                NotificationSubscription.template_id == tmpl_id,
                NotificationSubscription.status == 'active',
            ).first()
            if not sub:
                logger.info('[Notification] 二级审批人 %s 无可用订阅，跳过', approver.openid)
                continue

            ok = client.send_approval_notice(
                openid=approver.openid,
                visitor_name=visitor.name,
                department=visitor.host_department,
                visitor_id=visitor.id,
            )
            if ok:
                sub.status = 'used'
                sub.used_at = datetime.utcnow()
                logger.info('[Notification] 二级审批通知已发送: %s → %s', visitor.name, approver.name)
    except Exception:
        logger.exception('[Notification] 通知二级审批人异常，已忽略')


def _notify_visitor(visitor, status):
    """通知访客审批结果"""
    try:
        if not visitor.openid:
            return

        client = get_wx_client()
        tmpl_id = _get_template_id('RESULT_NOTICE')
        if not tmpl_id:
            return

        sub = NotificationSubscription.query.filter(
            NotificationSubscription.openid == visitor.openid,
            NotificationSubscription.template_id == tmpl_id,
            NotificationSubscription.status == 'active',
        ).first()
        if not sub:
            logger.info('[Notification] 访客 %s 无可用订阅，跳过', visitor.openid)
            return

        ok = client.send_result_notice(
            openid=visitor.openid,
            visitor_name=visitor.name,
            status=status,
            reason=visitor.reject_reason or '',
        )
        if ok:
            sub.status = 'used'
            sub.used_at = datetime.utcnow()
            logger.info('[Notification] 审批结果通知已发送: %s → %s (status=%s)',
                        visitor.name, visitor.openid, status)
    except Exception:
        logger.exception('[Notification] 通知访客异常，已忽略')


# ------------------------------------------------------------------
# 工具函数
# ------------------------------------------------------------------

def _was_l1_approver(visitor_id, approver_id):
    """
    判断某个审批人是否刚在本次事务中作为 L1 审批了该访客。
    通过双重检查确保精确匹配，避免误伤同部门其他 L1。

    1. session.new → 检查刚添加、尚未 flush 的 ApprovalRecord
    2. DB 查询   → flush 后但未 commit 的记录在同一事务内可见
    """
    from models.admin import ApprovalRecord

    # 方式1：遍历 session 中未 flush 的新对象
    for obj in db.session.new:
        if isinstance(obj, ApprovalRecord) \
                and obj.visitor_id == visitor_id \
                and obj.approver_role == 'level1' \
                and obj.result == 'approved':
            if obj.approver_id == approver_id:
                return True

    # 方式2：查询已 flush 但未 commit 的记录（同一事务内可见）
    with db.session.no_autoflush:
        last = ApprovalRecord.query.filter(
            ApprovalRecord.visitor_id == visitor_id,
            ApprovalRecord.approver_role == 'level1',
            ApprovalRecord.result == 'approved',
        ).order_by(ApprovalRecord.id.desc()).first()

    if last and last.approver_id == approver_id:
        return True

    return False


def _get_template_id(template_key):
    """从环境变量获取模板 ID"""
    import os
    var_name = f'WX_TMPL_{template_key}'
    return os.environ.get(var_name, '')


def refresh_notification_db(app):
    """
    确保 notification_subscriptions 表存在（幂等操作）。
    在 app.py 的 db.create_all() 之后调用。

    用法:
        from services.notification import refresh_notification_db
        refresh_notification_db(app)
    """
    with app.app_context():
        # 导入模型以触发 SQLAlchemy 元数据注册
        from models.notification import NotificationSubscription  # noqa: F401
        db.create_all()
        logger.info('[Notification] 数据库表确认完毕')
