  # 使用默认密码 Admin@123456 重置
  cd backend
  flask --app app reset-admin-password

  # 指定新密码
  flask --app app reset-admin-password --password MyNewP@ss123
