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

# Init / re-seed database
flask --app app seed-db

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

### 角色体系

Every user gets an `openid`. A single query to the `approvers` table (`auth.py:119`) determines role:

| approvers 表命中? | role | 小程序 tabBar |
|-------------------|------|-------------|
| 否 | `visitor` | 首页 / 我的 |
| 是, role=level1 | `level1` | 首页 / 待审批 / 审批记录 |
| 是, role=level2 | `level2` | 首页 / 待审批 / 审批记录 |

**Test env**: `app.js` persists a mock openid in wx.Storage and sends it as `mock_openid` on login. Use compile-mode startup params like `mock_openid=a_l1_001` to impersonate specific users. Pre-register approver openids directly in SQL.

**Prod env**: `auth.py:99-113` exchanges `wx.login()` code for real openid via WeChat `code2Session` API. Requires `WECHAT_APPID` + `WECHAT_SECRET` env vars.

### 审批流程（核心）

```
访客提交登记 → 状态=pending
  → 系统按 host_department 匹配一级审批人（approvers.department 相同）
  → 一级审批通过 → 检查是否需要二级:
      同部门? → 直接变为 approved
      不同部门? → 状态=level1_approved，等待二级审批
  → 二级审批通过 → approved，返回通行凭证（2小时有效）
```

Rejection sends status back to `pending` with a reason; visitor edits and resubmits.

### 敏感数据

- `services/crypto.py`: AES-256-CBC for phone/ID number storage; bcrypt for admin passwords
- Export (Excel): ID middle 10 digits → `*`, phone middle 4 digits → `*`
- Excel files have workbook password protection via `openpyxl.security`

### 环境切换

`config.py`: `ENV` env var → `DevelopmentConfig` | `ProductionConfig`. The config class auto-loads `DB_*`, `AES_KEY`, `SECRET_KEY` from os.environ. `get_config()` also stamps `.ENV` onto the class so the health-check endpoint can report it.

### 数据库

- `departments` — visitor host dept & level1 approver dept (shared)
- `level2_departments` — single-row table; enforced by backend check at insert
- `approvers` — `openid` + `role` + `is_registered`; `register_token` for invite links
- `visitors` — encrypted phone/id_number; `license_plates` is JSON array; `status` tracks approval state
- `companions` — child rows of visitor
- `approval_records` — audit log
- `system_config` — key-value store for welcome message, notice HTML, image URLs, Excel password
