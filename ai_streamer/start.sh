#!/bin/bash
# start.sh - 一键启动AI虚拟主播
# 用法: ./start.sh [房间号]

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🎭 AI虚拟主播启动脚本"
echo "======================"

# 获取房间号
ROOM_ID=${1:-""}

if [ -z "$ROOM_ID" ]; then
    echo -e "${YELLOW}提示: 可以直接带房间号启动，如: ./start.sh 123456${NC}"
    read -p "请输入B站直播间号: " ROOM_ID
fi

if [ -z "$ROOM_ID" ]; then
    echo -e "${RED}错误: 必须提供直播间号${NC}"
    exit 1
fi

# 检查是否在正确目录
if [ ! -f "main.py" ]; then
    echo -e "${RED}错误: 请在ai_streamer目录下运行此脚本${NC}"
    echo "正确用法: cd ai_streamer && ./start.sh 房间号"
    exit 1
fi

# 检查Python
echo ""
echo "🔍 检查环境..."

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}错误: 未找到python3，请先安装Python 3.8+${NC}"
    exit 1
fi

echo "✓ Python版本: $(python3 --version)"

# 检查依赖
echo ""
echo "📦 检查依赖..."

if ! python3 -c "import loguru" 2>/dev/null; then
    echo -e "${YELLOW}⚠ 依赖未安装，正在安装...${NC}"
    pip install -r requirements.txt
fi

echo "✓ 依赖已安装"

# 检查配置文件
echo ""
echo "⚙️  检查配置..."

if [ ! -f "config/api_keys.yaml" ]; then
    echo -e "${YELLOW}⚠ 配置文件不存在，正在创建...${NC}"
    cp config/api_keys.yaml.example config/api_keys.yaml
    echo -e "${RED}⚠ 请编辑 config/api_keys.yaml，填入你的Anthropic API Key${NC}"
    echo "启动取消"
    exit 1
fi

# 检查API Key是否已配置
if grep -q "your_api_key_here" config/api_keys.yaml; then
    echo -e "${RED}⚠ 请先编辑 config/api_keys.yaml，填入你的Anthropic API Key${NC}"
    exit 1
fi

echo "✓ 配置已设置"

# 检查记忆系统
echo ""
echo "🧠 检查记忆系统..."

if [ -d "../memory" ]; then
    echo "✓ 记忆系统已连接"
else
    echo -e "${YELLOW}⚠ 记忆系统目录不存在，运行初始化...${NC}"
    python3 scripts/init_memory.py
fi

# 创建日志目录
mkdir -p data/logs

# 启动选项
echo ""
echo "🚀 启动选项"
echo "=========="
echo "1) 纯聊天模式（推荐首次运行）"
echo "2) 测试模式（不连接弹幕，手动输入）"
echo "3) 带游戏控制"
echo "4) 退出"
echo ""

read -p "请选择 [1-4]: " choice

case $choice in
    1)
        echo ""
        echo -e "${GREEN}启动纯聊天模式...${NC}"
        echo "房间号: $ROOM_ID"
        echo "按 Ctrl+C 停止"
        echo ""
        python3 main.py --room $ROOM_ID
        ;;
    2)
        echo ""
        echo -e "${GREEN}启动测试模式...${NC}"
        echo "输入 'quit' 退出"
        echo ""
        python3 main.py --room $ROOM_ID --test
        ;;
    3)
        echo ""
        read -p "请输入游戏配置名(default: generic_web_game): " game_key
        game_key=${game_key:-"generic_web_game"}
        echo -e "${GREEN}启动游戏模式...${NC}"
        echo "房间号: $ROOM_ID"
        echo "游戏: $game_key"
        echo ""
        python3 main.py --room $ROOM_ID --game $game_key
        ;;
    4)
        echo "已取消"
        exit 0
        ;;
    *)
        echo -e "${RED}无效选择${NC}"
        exit 1
        ;;
esac
