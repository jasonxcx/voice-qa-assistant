@echo off
chcp 65001 >nul
echo ================================================
echo   实时问答助理 - 快速启动脚本
echo ================================================
echo.

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.10+
    pause
    exit /b 1
)

echo [1/4] 检查配置文件...
if not exist config.yaml (
    echo [提示] 复制 config.yaml.template 为 config.yaml
    copy config.yaml.template config.yaml
    echo.
    echo !!! 重要 !!!
    echo 请先编辑 config.yaml 配置 API Key
    echo 按任意键继续...
    pause >nul
)

echo [2/4] 检查依赖...
python -c "import PySide6" >nul 2>&1
if errorlevel 1 (
    echo [安装] 正在安装依赖，请稍候...
    pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
)

echo [3/4] 检查 PyTorch GPU 支持...
python -c "import torch; print(torch.cuda.is_available())" >nul 2>&1
if errorlevel 1 (
    echo.
    echo [提示] PyTorch 未安装或无 GPU 支持
    echo 如需 GPU 加速，请运行:
    echo pip install torch==2.5.1+cu118 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cu118
    echo.
)

echo [4/4] 启动程序...
echo.
python app.py
