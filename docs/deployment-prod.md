# 生产环境部署指南

## 一、生产环境准备清单

### 1.1 基础设施
| 项目 | 要求 | 说明 |
|------|------|------|
| 服务器 | Linux (RHEL 8+/Ubuntu 20.04+) | 建议 4核8G 以上 |
| 域名 | 已备案的域名 | 用于 HTTPS 和小程序配置 |
| SSL 证书 | 有效的SSL证书 | Let's Encrypt 免费或商业证书 |
| 微信小程序 AppID | 已注册的正式 AppID | 在微信公众平台注册 |
| 微信小程序 AppSecret | 配套的 AppSecret | 保密存储 |

### 1.2 软件环境
| 软件 | 版本 | 说明 |
|------|------|------|
| Python | 3.9+ | 建议使用 3.11 |
| MySQL | 8.0+ | 生产推荐使用云数据库 |
| Nginx | 1.20+ | 反向代理 + 静态文件 |
| Gunicorn | 21.x | WSGI 应用服务器 |
| Supervisor | 4.x | 进程守护 |

### 1.3 安全准备
- [ ] 生成强随机 SECRET_KEY（至少256位）
- [ ] 生成强随机 AES_KEY（32字节）
- [ ] 生成强随机 AES_IV（16字节）
- [ ] 设置强管理员密码
- [ ] 配置防火墙规则
- [ ] 配置数据库访问白名单

## 二、部署步骤

### 2.1 数据库配置
```bash
# 创建生产数据库
mysql -u root -p << EOF
CREATE DATABASE IF NOT EXISTS visitor_prod
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'visitor'@'localhost' IDENTIFIED BY 'strong_password_here';
GRANT ALL PRIVILEGES ON visitor_prod.* TO 'visitor'@'localhost';
FLUSH PRIVILEGES;
EOF

# 导入初始化脚本（注意修改数据库名）
sed 's/visitor_dev/visitor_prod/g' backend/migrations/init.sql | mysql -u root -p
```

### 2.2 应用部署
```bash
# 创建部署目录
sudo mkdir -p /opt/visitor-system
sudo chown $USER:$USER /opt/visitor-system

# 复制代码
cp -r backend/ /opt/visitor-system/
cp -r admin/ /opt/visitor-system/

# 安装依赖
cd /opt/visitor-system/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install gunicorn
```

### 2.3 环境变量配置
创建 `/opt/visitor-system/.env`：
```bash
export ENV=production
export SECRET_KEY="使用 openssl rand -hex 32 生成的随机字符串"
export AES_KEY="使用 openssl rand -hex 16 生成的32字节密钥"
export AES_IV="使用 openssl rand -hex 8 生成的16字节IV"
export DB_USER=visitor
export DB_PASSWORD=strong_password_here
export DB_HOST=127.0.0.1
export DB_NAME=visitor_prod
export PORT=5000
export JWT_EXPIRATION_HOURS=2
export EXCEL_PASSWORD="复杂的Excel密码"
export WECHAT_APPID=wx_your_appid
export WECHAT_SECRET=your_app_secret
```

### 2.4 Gunicorn 配置
创建 `/opt/visitor-system/gunicorn.conf.py`：
```python
bind = "127.0.0.1:5000"
workers = 4
worker_class = "sync"
timeout = 120
accesslog = "/var/log/visitor/access.log"
errorlog = "/var/log/visitor/error.log"
loglevel = "info"
```

### 2.5 Supervisor 配置
创建 `/etc/supervisord.d/visitor.ini`：
```ini
[program:visitor]
command=/opt/visitor-system/backend/venv/bin/gunicorn -c /opt/visitor-system/gunicorn.conf.py app:app
directory=/opt/visitor-system/backend
user=nobody
autostart=true
autorestart=true
stderr_logfile=/var/log/visitor/supervisor_err.log
stdout_logfile=/var/log/visitor/supervisor_out.log
environment=ENV="production"
```

```bash
# 启动应用
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start visitor
```

### 2.6 Nginx 配置
```nginx
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/ssl/certs/your-domain.pem;
    ssl_certificate_key /etc/ssl/private/your-domain.key;

    # 管理后台
    location /admin/ {
        alias /opt/visitor-system/admin/;
        index login.html;
    }

    # API 反代
    location /api/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # API 健康检查
    location /api/health {
        proxy_pass http://127.0.0.1:5000;
    }
}
```

```bash
sudo nginx -t
sudo systemctl reload nginx
```

### 2.7 小程序配置
1. 登录微信公众平台 (mp.weixin.qq.com)
2. 在「开发 → 开发管理 → 开发设置」中：
   - 配置服务器域名（request合法域名）：`https://your-domain.com`
   - 配置业务域名
3. 修改 `miniprogram/project.config.json` 中的 `appid` 为正式 AppID
4. 修改 `miniprogram/app.js` 中的 `baseUrl` 为 `https://your-domain.com`
5. 上传小程序代码并提交审核

## 三、生产环境检查清单

- [ ] 数据库使用强密码，已限制访问IP
- [ ] SECRET_KEY / AES_KEY / AES_IV 已替换为强随机值
- [ ] 管理员密码已更改为强密码
- [ ] SSL 证书已正确配置
- [ ] 防火墙已配置（仅开放 80/443）
- [ ] 微信小程序 AppID 和 AppSecret 已配置
- [ ] 数据库定时备份已配置
- [ ] 日志轮转已配置 (logrotate)
- [ ] Supervisor 进程守护已启动
- [ ] Nginx 反向代理正常
- [ ] API 接口可通过 HTTPS 访问
- [ ] 微信登录可正常调通

## 四、维护建议

### 4.1 数据库备份
```bash
# 每日备份脚本 (crontab)
0 3 * * * /usr/bin/mysqldump -u visitor -p'password' visitor_prod | gzip > /backup/visitor_$(date +\%Y\%m\%d).sql.gz
```

### 4.2 日志管理
```bash
# logrotate 配置
/var/log/visitor/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 nobody nobody
}
```

### 4.3 监控建议
- 使用 `uptime` / `systemctl status` 监控服务状态
- 配置日志告警关键字（ERROR、异常）
- 定期检查数据库连接池和慢查询
- 建议使用阿里云/腾讯云等云监控服务

## 五、故障处理

### 应用无法启动
```bash
# 检查日志
sudo tail -f /var/log/visitor/error.log
# 检查端口
sudo netstat -tlnp | grep 5000
# 手动启动测试
cd /opt/visitor-system/backend && source venv/bin/activate && python app.py
```

### 数据库连接失败
```bash
# 检查 MySQL 服务
sudo systemctl status mysqld
# 测试连接
mysql -u visitor -p -h 127.0.0.1 visitor_prod
```
