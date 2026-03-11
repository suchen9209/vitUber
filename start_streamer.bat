@echo off
chcp 65001 >nul
echo ==========================================
echo    AI虚拟主播启动脚本
echo ==========================================
echo.

REM 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到Python，请先安装Python 3.9+
    pause
    exit /b 1
)

REM 检查依赖
if not exist "ai_streamer\venv" (
    echo [1/3] 创建虚拟环境...
    python -m venv ai_streamer\venv
)

echo [2/3] 安装依赖...
call ai_streamer\venv\Scripts\activate.bat
pip install -q -r ai_streamer\requirements.txt

REM 检查Playwright
playwright show-browsers >nul 2>&1
if errorlevel 1 (
    echo [3/3] 安装浏览器...
    playwright install chromium
)

echo.
echo ==========================================
echo    启动选项:
echo ==========================================
echo.
echo 1. 测试模式 (推荐先跑这个)
echo 2. 正式直播模式
echo.
set /p choice="请选择 (1/2): "

if "%choice%"=="1" (
    echo.
    echo 启动测试模式...
    python ai_streamer\main.py --room 123456 --test
) else if "%choice%"=="2" (
    echo.
    set /p roomid="请输入B站直播间号: "
    echo.
    echo 启动直播模式...
    python ai_streamer\main.py --room %roomid%
) else (
    echo 无效选择
)

pause
