#!/bin/bash
# ============================================
# 访客登记系统 — 生产环境变量配置脚本
# 将环境变量写入 ~/.bashrc，实现永久生效
# ============================================

set -e

MARKER="# >>> 访客登记系统 prod 环境变量 <<<"

# 安全敏感变量请在此处填写实际值
VARS='export ENV=production
export SECRET_KEY=<请替换为强随机字符串>
export AES_KEY=<请替换为32字节AES密钥>
export AES_IV=<请替换为16字节AES向量>
export DB_USER=visitor
export DB_PASSWORD=<请替换为数据库密码>
export DB_HOST=127.0.0.1
export DB_PORT=3306
export DB_NAME=visitor_prod
export WECHAT_APPID=<请替换为微信AppID>
export WECHAT_SECRET=<请替换为微信AppSecret>
export EXCEL_PASSWORD=<请替换为Excel导出密码>
export PORT=5000
'

# 如果已存在则先清理旧配置
if grep -q "$MARKER" ~/.bashrc 2>/dev/null; then
    echo "检测到已有旧配置，正在更新…"
    sed -i "/$MARKER/,/$MARKER/d" ~/.bashrc
fi

# 写入新配置
{
    echo ""
    echo "$MARKER"
    echo -n "$VARS"
    echo "$MARKER"
} >> ~/.bashrc

echo "⚠️  请先编辑此脚本，将 <请替换为…> 的占位符替换为实际值后重新运行！"
echo ""
echo "环境变量已写入 ~/.bashrc"
echo ""
echo "变量列表："
echo "  ENV=production"
echo "  SECRET_KEY=***"
echo "  AES_KEY=***"
echo "  AES_IV=***"
echo "  DB_USER=visitor"
echo "  DB_PASSWORD=***"
echo "  DB_HOST=127.0.0.1"
echo "  DB_PORT=3306"
echo "  DB_NAME=visitor_prod"
echo "  WECHAT_APPID=***"
echo "  WECHAT_SECRET=***"
echo "  EXCEL_PASSWORD=***"
echo "  PORT=5000"
echo ""
echo "执行以下命令使其在当前终端立即生效："
echo "  source ~/.bashrc"
