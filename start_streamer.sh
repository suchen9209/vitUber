#!/bin/bash
# AI虚拟主播启动脚本 (Linux/Mac)

echo "=========================================="
echo "   AI虚拟主播启动脚本"
echo "=========================================="
echo ""

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "[错误] 未找到Python3"
    exit 1
fi

# 创建虚拟环境
if [ ! -d "ai_streamer/venv" ]; then
    echo "[1/3] 创建虚拟环境..."
    python3 -m venv ai_streamer/venv
fi

# 安装依赖
echo "[2/3] 安装依赖..."
source ai_streamer/venv/bin/activate
pip install -q -r ai_streamer/requirements.txt

# 检查Playwright
echo "[3/3] 检查浏览器..."
playwright show-browsers || playwright install chromium

echo ""
echo "=========================================="
echo "   启动选项:"
echo "=========================================="
echo ""
echo "1. 测试模式 (推荐先跑这个)"
echo "2. 正式直播模式"
echo "3. 退出"
echo ""

read -p "请选择 (1/2/3): " choice

if [ "$choice" == "1" ]; then
    echo ""
    echo "启动测试模式..."
    python ai_streamer/main.py --room 123456 --test
elif [ "$choice" == "2" ]; then
    echo ""
    read -p "请输入B站直播间号: " roomid
    echo ""
    echo "启动直播模式..."
    python ai_streamer/main.py --room "$roomid"
else
    echo "退出"
fi
