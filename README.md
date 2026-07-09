# 访客登记系统

基于微信小程序 + Python Flask + MySQL 的访客登记与审批管理系统。

## 功能概览

- **访客端**：微信小程序登记、告知书确认、查看审批结果和通行凭证
- **审批端**：二级审批流程、待审批列表、审批历史
- **管理端**：Web后台管理系统、Excel导出（密码保护+数据脱敏）

## 快速开始（测试环境）

### 1. 数据库初始化
```bash
mysql -u root -p < backend/migrations/init.sql
```

### 2. 后端启动
```bash
cd backend
pip install -r requirements.txt
set ENV=development        # Windows
# export ENV=development   # Linux/Mac
python app.py
```

### 3. 初始化数据
```bash
flask --app app seed-db
```

### 4. 微信小程序
使用微信开发者工具导入 `miniprogram/` 目录

### 5. 管理后台
访问 http://127.0.0.1:5000/admin/login.html
- 默认账号: admin
- 默认密码: Admin@123456

## 目录结构

```
├── backend/           # Python Flask 后端
├── miniprogram/       # 微信小程序前端
├── admin/             # Web 管理后台
├── docs/              # 部署文档
└── 需求.md            # 需求文档
```

## 详细文档

- [测试环境部署](docs/deployment-test.md)
- [生产环境部署](docs/deployment-prod.md)
