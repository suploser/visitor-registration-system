  # 使用默认密码 Admin@123456 重置
  cd backend
  flask --app app reset-admin-password

  # 指定新密码
  flask --app app reset-admin-password --password MyNewP@ss123
  
  # 在生产服务器上，需要先加载环境变量再执行命令，否则会连接到错误的数据库：
  # 1. SSH 到生产服务器
  # 2. 加载环境变量并执行
  cd /opt/visitor-system/backend  source ../.env
  flask --app app reset-admin-password --password 新密码
  或者一行搞定（不依赖 .env 文件）：

  cd /opt/visitor-system/backend && ENV=production DB_USER=visitor DB_PASSWORD=你的DB密码 DB_NAME=visitor_prod flask --app app reset-admin-password --password 新密码
