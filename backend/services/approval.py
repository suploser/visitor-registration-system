"""
审批流程服务
"""
from datetime import datetime, timedelta
from models import db
from models.approver import Approver
from models.admin import ApprovalRecord


class ApprovalService:
    """审批流程管理"""

    @staticmethod
    def find_level1_approver(department: str):
        """根据部门查找一级审批人"""
        return Approver.query.filter_by(
            department=department,
            role='level1',
            is_registered=True
        ).first()

    @staticmethod
    def find_level2_approver():
        """查找二级审批人（返回第一个）"""
        return Approver.query.filter_by(
            role='level2',
            is_registered=True
        ).first()

    @staticmethod
    def get_all_level2_approvers():
        """获取所有二级审批人"""
        return Approver.query.filter_by(
            role='level2',
            is_registered=True
        ).all()

    @staticmethod
    def get_pending_approvals(approver):
        """获取审批人的待审批列表（多角色/多部门自动合并）"""
        from models.visitor import Visitor

        # 查出该 openid 下的所有审批人记录
        all_my_roles = Approver.query.filter(
            Approver.openid == approver.openid,
            Approver.is_registered == True
        ).all()

        # 收集该人所有的 level1 部门（去重）
        level1_depts = list(set(
            a.department for a in all_my_roles if a.role == 'level1'
        ))
        # 是否也是二级审批人
        is_also_level2 = any(a.role == 'level2' for a in all_my_roles)

        visitors = []

        # 一级审批项：所有 level1 部门中的 pending 记录
        if level1_depts:
            level1_visitors = Visitor.query.filter(
                Visitor.host_department.in_(level1_depts),
                Visitor.status == 'pending',
                Visitor.session_expires > datetime.now()
            ).order_by(Visitor.created_at.desc()).all()
            visitors.extend(level1_visitors)

        # 二级审批项：如果该人是二级审批人，追加所有 level1_approved 记录
        if is_also_level2 or approver.role == 'level2':
            level2_visitors = Visitor.query.filter(
                Visitor.status == 'level1_approved',
                Visitor.session_expires > datetime.now()
            ).order_by(Visitor.created_at.desc()).all()
            visitors.extend(level2_visitors)

        return visitors

    @staticmethod
    def approve(visitor_id, approver, result, comment=''):
        """
        执行审批操作（双角色者根据访客状态自动切换审批身份）
        返回 (success, message)
        """
        from models.visitor import Visitor

        visitor = Visitor.query.get(visitor_id)
        if not visitor:
            return False, '登记记录不存在'

        if visitor.session_expires and visitor.session_expires < datetime.now():
            return False, '访客会话已过期'

        # 多角色/多部门兼容：根据访客状态和部门自动匹配正确的审批身份
        effective_approver = approver
        if approver.role == 'level1' and visitor.status == 'level1_approved':
            # 作为一级审批人，但访客需要二级审批 → 切换到该人的二级身份
            other = Approver.query.filter_by(
                openid=approver.openid, role='level2', is_registered=True
            ).first()
            if other:
                effective_approver = other
        elif approver.role == 'level1' and visitor.status == 'pending' \
                and visitor.host_department != approver.department:
            # 部门不匹配 → 查找该人在访客部门的一级审批人记录
            other = Approver.query.filter_by(
                openid=approver.openid, role='level1',
                department=visitor.host_department, is_registered=True
            ).first()
            if other:
                effective_approver = other
        elif approver.role == 'level2' and visitor.status == 'pending':
            # 作为二级审批人，但访客需要一级审批 → 切换到该人的一级身份
            other = Approver.query.filter_by(
                openid=approver.openid, role='level1',
                department=visitor.host_department, is_registered=True
            ).first()
            if not other:
                # 任意部门的一级身份也行
                other = Approver.query.filter_by(
                    openid=approver.openid, role='level1', is_registered=True
                ).first()
            if other:
                effective_approver = other

        # 检查审批权限
        if effective_approver.role == 'level1':
            if visitor.host_department != effective_approver.department:
                return False, '您不是该访客接待部门的一级审批人'
            if visitor.status != 'pending':
                return False, '该登记已审批，无需重复操作'
        elif effective_approver.role == 'level2':
            if visitor.status != 'level1_approved':
                return False, '该登记尚未通过一级审批'
        else:
            return False, '无效的审批人角色'

        # 创建审批记录
        record = ApprovalRecord(
            visitor_id=visitor_id,
            approver_id=effective_approver.id,
            approver_name=effective_approver.name,
            approver_role=effective_approver.role,
            result=result,
            comment=comment,
        )
        db.session.add(record)

        if result == 'rejected':
            # 拒绝：状态设为rejected，访客可修改后重新提交
            visitor.status = 'rejected'
            visitor.reject_reason = comment or '审批未通过，请核对信息后重新提交'
            db.session.commit()
            return True, '已拒绝该访客登记申请'

        # 审批通过
        if effective_approver.role == 'level1':
            # 检查是否需要二级审批
            level2_all = ApprovalService.get_all_level2_approvers()
            if not level2_all:
                # 没有二级审批人，直接通过
                visitor.status = 'approved'
                visitor.reject_reason = None
                visitor.session_expires = datetime.now() + timedelta(hours=2)
                db.session.commit()
                return True, '审批通过（系统中未录入二级审批人，无需二级审批），访客可查看通行凭证'

            # 所有二级审批人都是一级审批人本人 → 无需重复审批
            if all(l2.openid == effective_approver.openid for l2 in level2_all):
                visitor.status = 'approved'
                visitor.reject_reason = None
                visitor.session_expires = datetime.now() + timedelta(hours=2)
                db.session.commit()
                return True, '审批通过（您同时是一级和二级审批人，无需重复审批），访客可查看通行凭证'

            # 存在不同的二级审批人 → 转二级审批
            level2 = level2_all[0]
            visitor.status = 'level1_approved'
            visitor.reject_reason = None
            db.session.commit()
            return True, f'一级审批通过，已转二级审批人（{level2.name}，{level2.department}）进行审批'

        elif effective_approver.role == 'level2':
            # 二级审批通过
            visitor.status = 'approved'
            visitor.reject_reason = None
            visitor.session_expires = datetime.now() + timedelta(hours=2)
            db.session.commit()
            return True, '审批通过，访客可查看通行凭证'

        db.session.commit()
        return True, '操作成功'

    @staticmethod
    def get_approval_history(approver):
        """获取审批人的审批历史"""
        records = ApprovalRecord.query.filter_by(
            approver_id=approver.id
        ).order_by(ApprovalRecord.approved_at.desc()).all()
        return records
