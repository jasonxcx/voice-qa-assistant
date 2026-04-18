@echo off
REM 无控制台启动脚本
REM 使用 pythonw 启动，不会有控制台窗口

REM 检查 Python
pythonw --version >nul 2>&1
if errorlevel 1 (
    echo [错误] pythonw 未找到
    pause
    exit /b 1
)

REM 检查配置文件
if not exist config.yaml (
    copy config.yaml.template config.yaml
)

REM 直接启动程序（pythonw 无窗口）
start "" pythonw app.py
REM 等待1秒确保程序启动
timeout /t 1 /nobreak >nul
REM 关闭自身窗口
exit