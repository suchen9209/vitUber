#!/bin/bash
# start-companion.sh
# 赛博陪伴直播一键启动脚本

set -e

echo "🌙 启动赛博陪伴直播..."
echo ""

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 需要安装 Python3"
    exit 1
fi

# 检查记忆系统
echo "📁 检查记忆系统..."
MEMORY_DIR="/root/.openclaw/workspace/memory"

if [ ! -d "$MEMORY_DIR" ]; then
    echo "❌ 错误: 记忆系统目录不存在"
    echo "   路径: $MEMORY_DIR"
    exit 1
fi

echo "   ✅ 记忆系统已就绪"

# 检查关键文件
FILES=(
    "memes/current-hot.md"
    "common-sense/world-events.md"
)

for file in "${FILES[@]}"; do
    if [ -f "$MEMORY_DIR/$file" ]; then
        echo "   ✅ $file"
    else
        echo "   ⚠️  $file (不存在，将使用默认内容)"
    fi
done

echo ""

# 运行测试
echo "🧪 运行快速测试..."
python3 "$MEMORY_DIR/scripts/cyber_companion.py" --test

# 询问是否启动
echo ""
read -p "是否启动直播? (y/N): " confirm

if [[ $confirm =~ ^[Yy]$ ]]; then
    echo ""
    echo "🎙️  直播已启动"
    echo "   按 Ctrl+C 停止"
    echo ""
    python3 "$MEMORY_DIR/scripts/cyber_companion.py"
else
    echo ""
    echo "👋 已取消"
fi
