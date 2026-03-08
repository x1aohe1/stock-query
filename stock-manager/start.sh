#!/bin/bash

# Stock Manager API 启动脚本

cd "$(dirname "$0")"

echo "🚀 启动 Stock Quote API..."
echo "📍 工作目录：$(pwd)"
echo "🔌 端口：8002"
echo "📖 文档：http://localhost:8002/docs"
echo ""

# 检查并安装依赖
if [ ! -f "backend/.installed" ]; then
    echo "📦 安装依赖..."
    pip3 install -r backend/requirements.txt
    touch backend/.installed
    echo "✅ 依赖安装完成"
fi

# 启动服务
echo " 启动服务..."
cd backend
python3 api.py
