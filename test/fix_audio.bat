@echo off
chcp 65001 >nul
echo ============================================================
echo 音频配置修复工具
echo ============================================================
echo.

echo 步骤 1: 检查 VB-Cable 是否已安装
echo ----------------------------------------
echo 如果未安装，请访问：https://vb-audio.com/Cable/
echo 下载并安装后重启电脑
echo.
pause

echo.
echo 步骤 2: 配置 Windows 声音输出
echo ----------------------------------------
echo 1. 右键点击任务栏喇叭图标
echo 2. 选择"声音设置"或"声音"
echo 3. 在"输出"或"播放"选项卡中
echo 4. 找到 "CABLE Input" 或 "VB-Audio Virtual Cable"
echo 5. 右键 - 设为默认设备
echo.
echo 按任意键打开 Windows 声音设置...
pause
start mmsys.cpl

echo.
echo 步骤 3: 配置 VB-Cable 监听（让你能听到声音）
echo ----------------------------------------
echo 1. 在"录制"选项卡中
echo 2. 找到 "CABLE Output" 或 "VB-Audio Point"
echo 3. 右键 - 属性
echo 4. 勾选"侦听此设备"
echo 5. "通过此设备播放"选择你的扬声器/耳机
echo 6. 确定
echo.
echo 配置完成后按任意键继续...
pause

echo.
echo 步骤 4: 测试音频输入
echo ----------------------------------------
python test_audio.py

echo.
echo 按任意键退出...
pause >nul
