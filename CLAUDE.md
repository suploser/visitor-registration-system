# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Quick Commands

```bash
# Backend — start dev server (from backend/)
cd backend
pip install -r requirements.txt     # first time only
set ENV=development                  # Windows
export ENV=development               # Linux/Mac
python app.py                        # http://127.0.0.1:5000

# Init / re-seed database (creates tables + seed data)
flask --app app seed-db

# Init tables only (no seed data)
flask --app app init-db

# Reset admin password
flask --app app reset-admin-password
flask --app app reset-admin-password --password 新密码

# Health check
curl http://localhost:5000/api/health
```

Admin panel: `http://127.0.0.1:5000/admin/login.html` (admin / Admin@123456)

Mini program: open `miniprogram/` in WeChat DevTools, configure `baseUrl` in `app.js` to point at the backend.

## Architecture

```
微信小程序 (miniprogram/)  ←→  Flask API (backend/)  ←→  MySQL
                                  ↑
                           Web 管理后台 (admin/)
```

### 项目结构

```
miniprogram/
  app.js / app.json / app.wxss               # 小程序入口、全局配置、样式
  pages/
    index/           首页（公告、快捷操作）
    notice/          访客告知书（阅读倒计时后进入登记）
    register/        访客登记表单
    result/          审批结果 & 通行凭证
    approval-list/   待审批列表（审批人）
    approval-detail/ 审批详情 & 审批操作
    approval-history/审批记录
    approver-register/审批人注册（通过邀请 token）
  components/
    license-plate/   车牌输入组件
    companion-form/  同行人表单组件
  utils/
    api.js           请求封装（Bearer token, 401 处理）
    constants.js     访问目的等常量
    subscribe.js     订阅消息工具（授权弹窗 & 上报）

backend/
  app.py                  Flask 入口（工厂 + 定时任务 + CLI）
  config.py               DevelopmentConfig / ProductionConfig
  models/
    __init__.py           db = SQLAlchemy()
    visitor.py            Visitor + Companion（加密字段）
    approver.py           Approver（审批人 + 注册 token）
    department.py         Department + Level2Department
    admin.py              Admin + SystemConfig + ApprovalRecord
    notification.py       NotificationSubscription（订阅消息记录）
    verification_code.py
  routes/
    auth.py               /api/auth/wechat-login, /api/auth/admin-login
    visitor.py            /api/visitor/register, /status, /credential, /departments
    approver.py           /api/approver/pending, /approve, /history, /register
    admin.py              /api/admin/visitors, /approvers, /departments, /config, /export
    system.py             /api/config/public
    notification.py       /api/notification/subscribe, /templates, /status
  services/
    approval.py           ApprovalService（审批流程 + 权限校验）
    crypto.py             AES-256-CBC / bcrypt
    export.py             Excel 导出（脱敏 + 密码保护）
    notification.py       通知引擎（SQLAlchemy 事件监听）
    wx_subscribe.py       微信订阅消息 API 客户端
  migrations/
    add_notification_tables.sql

admin/
  login.html              管理后台登录页
  index.html              管理后台主页（访客管理、审批人管理、部门管理、系统配置、数据导出）
```

### 角色体系

Every user gets an `openid`. A single query to the `approvers` table (`auth.py:119`) determines role:

| approvers 表命中? | role | 小程序 tabBar |
|-------------------|------|-------------|
| 否 | `visitor` | 首页 / 我的 |
| 是, role=level1 | `level1` | 首页 / 待审批 / 审批记录 |
| 是, role=level2 | `level2` | 首页 / 待审批 / 审批记录 |

**关键细节**：同一个 `openid` 可以在 `approvers` 表中有多条记录（既是 level1 又是 level2，或者多个部门的 level1）。`auth.py:129` 用 `all_roles` 返回所有已注册角色；审批时 `ApprovalService.approve()` 根据访客状态自动切换审批身份。

**测试环境**：`app.js` persists a mock openid in wx.Storage and sends it as `mock_openid` on login. Use compile-mode startup params like `mock_openid=a_l1_001` to impersonate specific users. Pre-register approver openids directly in SQL. 后端 `auth.py:102-108` 检测到 `DEBUG=True` 时直接使用前端传入的 `mock_openid`。

**生产环境**：`auth.py:109-123` exchanges `wx.login()` code for real openid via WeChat `code2Session` API. Requires `WECHAT_APPID` + `WECHAT_SECRET` env vars. `baseUrl` 需改为生产服务器域名。

### 审批流程（核心）

```
访客提交登记 → 状态=pending
  ├─ 无 L1 审批人 & 无 L2 审批人 → 保持 pending（无通知，靠定时任务过期清理）
  ├─ 无 L1 审批人 & 有 L2 审批人 → 直接 level1_approved，通知 L2
  └─ 有 L1 审批人 → 通知 L1
       └─ L1 审批:
            拒绝 → rejected（通知访客，可修改后重新提交）
            通过 → 检查是否需要二级:
              所有 L2 都是该 L1 本人 → 直接 approved（通知访客）
              没有 L2 → 直接 approved（通知访客）
              有不同 L2 → level1_approved（通知 L2）
                └─ L2 审批:
                    拒绝 → rejected（通知访客）
                    通过 → approved（通知访客，2小时有效通行凭证）
```

`approval.py:166` 的 `all(l2.openid == approver.openid)` 检查防止同一人既是 L1 又是唯一的 L2 时给自己重复审批。

多 L1 场景：同一部门的所有 L1 审批人都能看到 `pending` 记录，任一通过即生效。`approval.py:101-122` 处理跨部门/多角色的审批权限切换。

### 定时任务

`app.py:71-73`：APScheduler 每 10 分钟清理过期会话。`session_expires < now` 的 pending/level1_approved 记录 → 状态改为 `rejected`，原因设为「会话已过期」。

### 订阅消息通知系统（仅生产环境）

通过 SQLAlchemy `after_insert` / `after_update` 事件监听 Visitor 变更，零侵入现有业务代码。

**入口**：`services/notification.py:init_notification(app)` — 仅在 `DEBUG=False` 时注册事件监听。

**触发链**：
```
Visitor INSERT/UPDATE
  → _on_visitor_created / _on_visitor_updated（检测 status 变更）
  → _handle_status_transition（状态 → 通知类型映射）
  → _notify_level1_approvers / _notify_level2_approvers / _notify_visitor
  → NotificationSubscription 查询 active 订阅
  → WxSubscribeClient.send_*() → 微信 API → 成功 → 标记 used
```

**关键设计**：
- 所有异常静默捕获，审批主流程不受影响
- L2 通知时跳过刚审批 L1 的同一人（`_was_l1_approver()` 双重检查：`session.new` + `no_autoflush`）
- 订阅是一次性的：发送成功后 `status` 从 `active` → `used`

**前端订阅**：`subscribe.js` 封装 `wx.requestSubscribeMessage`，先查余量（`/api/notification/status`），`active_count > 0` 则跳过弹窗，避免反复骚扰用户。

### 敏感数据

- `services/crypto.py`: AES-256-CBC for phone/ID number storage; bcrypt for admin passwords
- Export (Excel): ID middle 10 digits → `*`, phone middle 4 digits → `*`
- Excel files have workbook password protection

### 环境切换

`config.py`: `ENV` env var → `DevelopmentConfig` | `ProductionConfig`. The config class auto-loads `DB_*`, `AES_KEY`, `SECRET_KEY` from os.environ. `get_config()` also stamps `.ENV` onto the class so the health-check endpoint can report it.

生产环境额外需要：`WECHAT_APPID`, `WECHAT_SECRET`, `WX_TMPL_APPROVAL_NOTICE`, `WX_TMPL_RESULT_NOTICE`。

### 数据库表

| 表 | 用途 | 关键字段 |
|----|------|---------|
| `departments` | 部门（L1 审批人按部门匹配） | id, name |
| `level2_departments` | 二级审批人部门（单行约束） | id, name |
| `approvers` | 审批人注册信息 | openid, role, department, is_registered, register_token |
| `visitors` | 访客登记（加密字段） | openid, status, encrypted_phone/id_number, license_plates(JSON), session_expires |
| `companions` | 同行人 | visitor_id, name, encrypted_id_number |
| `approval_records` | 审批审计日志 | visitor_id, approver_id, result, comment |
| `notification_subscriptions` | 订阅消息记录 | openid, template_id, status(active/used) |
| `system_config` | 键值配置 | config_key, config_value |
| `admins` | 管理员账户 | username, password_hash, password_changed_at |
| `verification_codes` | 审批人注册验证码 | code, created_at |
