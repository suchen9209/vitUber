@echo off
chcp 65001 > nul
REM start.bat - 一键启动AI虚拟主播 (Windows版)
REM 用法: start.bat [房间号]

echo 🎭 AI虚拟主播启动脚本
echo ======================

REM 获取房间号
set ROOM_ID=%1

if "%ROOM_ID%"=="" (
    echo 提示: 可以直接带房间号启动，如: start.bat 123456
    set /p ROOM_ID="请输入B站直播间号: "
)

if "%ROOM_ID%"=="" (
    echo 错误: 必须提供直播间号
    exit /b 1
)

REM 检查是否在正确目录
if not exist "main.py" (
    echo 错误: 请在ai_streamer目录下运行此脚本
    echo 正确用法: cd ai_streamer && start.bat 房间号
    exit /b 1
)

REM 检查Python
echo.
echo 🔍 检查环境...

python --version > nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到python，请先安装Python 3.8+
    exit /b 1
)

for /f "tokens=*" %%a in ('python --version') do echo ✓ Python版本: %%a

REM 检查依赖
echo.
echo 📦 检查依赖...

python -c "import loguru" > nul 2>&1
if errorlevel 1 (
    echo ⚠ 依赖未安装，正在安装...
    pip install -r requirements.txt
)

echo ✓ 依赖已安装

REM 检查配置文件
echo.
echo ⚙️ 检查配置...

if not exist "config\api_keys.yaml" (
    echo ⚠ 配置文件不存在，正在创建...
    copy config\api_keys.yaml.example config\api_keys.yaml
    echo ⚠ 请编辑 config\api_keys.yaml，填入你的Anthropic API Key
    echo 启动取消
    exit /b 1
)

findstr /C:"your_api_key_here" config\api_keys.yaml > nul
if not errorlevel 1 (
    echo ⚠ 请先编辑 config\api_keys.yaml，填入你的Anthropic API Key
    exit /b 1
)

echo ✓ 配置已设置

REM 检查记忆系统
echo.
echo 🧠 检查记忆系统...

if exist "..\memory" (
    echo ✓ 记忆系统已连接
) else (
    echo ⚠ 记忆系统目录不存在，运行初始化...
    python scripts\init_memory.py
)

REM 创建日志目录
if not exist "data\logs" mkdir data\logs

REM 启动选项
echo.
echo 🚀 启动选项
echo ==========
echo 1) 纯聊天模式（推荐首次运行）
echo 2) 测试模式（不连接弹幕，手动输入）
echo 3) 带游戏控制
echo 4) 退出
echo.

set /p choice="请选择 [1-4]: "

if "%choice%"=="1" (
    echo.
    echo 启动纯聊天模式...
    echo 房间号: %ROOM_ID%
    echo 按 Ctrl+C 停止
    echo.
    python main.py --room %ROOM_ID%
) else if "%choice%"=="2" (
    echo.
    echo 启动测试模式...
    echo 输入 'quit' 退出
    echo.
    python main.py --room %ROOM_ID% --test
) else if "%choice%"=="3" (
    echo.
    set /p game_key="请输入游戏配置名(default: generic_web_game): "
    if "!game_key!"=="" set game_key=generic_web_game
    echo 启动游戏模式...
    echo 房间号: %ROOM_ID%
    echo 游戏: !game_key!
    echo.
    python main.py --room %ROOM_ID% --game !game_key!
) else if "%choice%"=="4" (
    echo 已取消
    exit /b 0
) else (
    echo 无效选择
    exit /b 1
)
