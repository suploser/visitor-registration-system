# 测试环境部署指南

## 测试环境架构

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  电脑A (Windows) │     │  电脑B (Windows) │     │  电脑C (RHEL)   │
│ 微信开发者工具     │     │ 微信开发者工具     │     │ Python后端+MySQL │
│ 模拟访客操作      │     │ 模拟审批人操作     │     │ 管理后台         │
└─────────────────┘     └─────────────────┘     └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                         局域网 HTTP 通信
```

## 一、后端部署（电脑C - RHEL）

### 1.1 环境要求
- RHEL 7/8/9 或 CentOS 7/8/9
- Python 3.9+
- MySQL 8.0+

### 1.2 安装 MySQL
```bash
# RHEL/CentOS 8+
sudo dnf install mysql-server
sudo systemctl start mysqld
sudo systemctl enable mysqld

# 设置 root 密码
sudo mysql_secure_installation
```

### 1.3 初始化数据库
```bash
mysql -u root -p < backend/migrations/init.sql
```

### 1.4 安装 Python 依赖
```bash
cd backend/
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 1.5 配置环境变量
```bash
export ENV=development
export DB_USER=root
export DB_PASSWORD=root
export DB_HOST=127.0.0.1
export DB_NAME=visitor_dev
export PORT=5000
```

> **注意**：`DB_PASSWORD` 需与 MySQL root 实际密码一致。若安装MySQL时未设密码则留空或设为 `''`。
> 若遇到 `Access denied` 错误，请检查 MySQL root 密码并相应设置此变量。

### 1.6 启动后端服务
```bash
# 开发模式
python app.py

# 或使用 Flask CLI
flask --app app run --host=0.0.0.0 --port=5000
```

### 1.7 初始化种子数据
```bash
flask --app app seed-db
```

### 1.8 验证后端运行
```bash
curl http://localhost:5000/api/health
# 应返回: {"env":"development","status":"ok"}
```

## 二、小程序前端部署（电脑A和电脑B - Windows）

### 2.1 安装微信开发者工具
- 下载地址: https://developers.weixin.qq.com/miniprogram/dev/devtools/download.html
- 安装后使用测试号或已注册的 AppID

### 2.2 配置项目
1. 打开微信开发者工具，导入项目
2. 选择 `miniprogram/` 目录
3. 修改 `project.config.json` 中的 `appid` 为你的测试号 AppID
4. 修改 `app.js` 中 `globalData.baseUrl` 为后端服务器地址：
   ```javascript
   baseUrl: 'http://192.168.x.x:5000'  // 替换为电脑C的IP地址
   ```

### 2.3 模拟多角色（多台电脑/多个DevTools实例）

通过微信开发者工具的 **「添加编译模式」**，每台电脑设置不同的 `mock_openid` 启动参数来实现多身份。

#### 编译模式设置方法

微信开发者工具 → 工具栏点击 **「普通编译」** 下拉 → **「添加编译模式」**：

**电脑A - 访客**：
| 字段 | 值 |
|------|-----|
| 模式名称 | `访客模式` |
| 启动页面 | `pages/index/index` |
| 启动参数 | `mock_openid=v_001` |

**电脑B - 一级审批人**：
| 字段 | 值 |
|------|-----|
| 模式名称 | `一级审批人` |
| 启动页面 | `pages/index/index` |
| 启动参数 | `mock_openid=a_l1_001` |

**电脑C - 二级审批人**（可选）：
| 字段 | 值 |
|------|-----|
| 模式名称 | `二级审批人` |
| 启动页面 | `pages/index/index` |
| 启动参数 | `mock_openid=a_l2_001` |

#### 在数据库中绑定审批人身份

审批人编译模式设置后**不会自动成为审批人**，需要先在 `approvers` 表中写入对应的 openid：

```sql
-- 一级审批人（技术部）
INSERT INTO approvers (openid, name, department, role, is_registered, register_token, token_expires)
VALUES ('a_l1_001', '张经理', '技术部', 'level1', 1, NULL, NULL);

-- 二级审批人
INSERT INTO approvers (openid, name, department, role, is_registered, register_token, token_expires)
VALUES ('a_l2_001', '李主任', '安全保卫部', 'level2', 1, NULL, NULL);
```

> **注意**：审批人的 `department` 必须与访客填写的 `host_department` 匹配才能收到待审批通知。

#### 启动参数说明

| 参数 | 效果 |
|------|------|
| `mock_openid=v_001` | 以访客001身份登录 |
| `mock_openid=a_l1_001` | 以审批人001身份登录（须DB中有记录） |
| `mock_openid=reset` | 清除旧身份，随机生成新的访客openid |
| 不传参数 | 使用上次缓存的openid（WiFi真机调试时使用） |

### 2.4 测试场景操作

1. **电脑A** 选择「访客模式」编译 → 进入小程序 → 首页 → 告知书 → 填写登记 → 提交
2. **电脑B** 选择「一级审批人」编译 → 首页显示「待审批」→ 查看详情 → 通过/拒绝
3. 若一级审批通过且部门不匹配 → **电脑C**（二级审批人）处理
4. 审批通过后 **电脑A** 切换到「我的」→ 查看通行凭证

## 三、管理后台

访问 `http://<服务器IP>:5000/admin/login.html`
- 默认账号: `admin`
- 默认密码: `Admin@123456`

## 四、测试检查清单

- [ ] 后端服务正常启动，API 返回正确
- [ ] 访客可正常登录小程序
- [ ] 首页显示欢迎弹窗
- [ ] 访客告知书可正常查看和勾选
- [ ] 登记表单可正常提交
- [ ] 审批人可查看待审批列表
- [ ] 一级审批流程正常
- [ ] 二级审批流程正常
- [ ] 审批通过后显示凭证
- [ ] 审批拒绝后可重新提交
- [ ] 管理后台可查看访客记录
- [ ] 管理后台可导出Excel（含密码保护）
- [ ] Excel 中身份证号和手机号已脱敏
- [ ] 2小时后会话正常过期
