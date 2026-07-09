#!/bin/bash
# ============================================
# 访客登记系统 — 开发环境变量配置脚本
# 将环境变量写入 ~/.bashrc，实现永久生效
# ============================================

set -e

MARKER="# >>> 访客登记系统 dev 环境变量 <<<"

# 要写入的变量
VARS='
export ENV=development
export DB_USER=root
export DB_PASSWORD=root
export DB_HOST=127.0.0.1
export DB_NAME=visitor_dev
export PORT=5000
'

# 如果已存在则先清理旧配置
if grep -q "$MARKER" ~/.bashrc 2>/dev/null; then
    echo "检测到已有旧配置，正在更新…"
    # 删除标记之间的旧内容（含标记行）
    sed -i "/$MARKER/,/$MARKER/d" ~/.bashrc
fi

# 写入新配置
{
    echo ""
    echo "$MARKER"
    echo -n "$VARS"
    echo "$MARKER"
} >> ~/.bashrc

echo "环境变量已写入 ~/.bashrc"
echo ""
echo "变量列表："
echo "  ENV=development"
echo "  DB_USER=root"
echo "  DB_PASSWORD=root"
echo "  DB_HOST=127.0.0.1"
echo "  DB_NAME=visitor_dev"
echo "  PORT=5000"
echo ""
echo "执行以下命令使其在当前终端立即生效："
echo "  source ~/.bashrc"
echo ""
echo "之后新打开的终端将自动加载这些环境变量。"
