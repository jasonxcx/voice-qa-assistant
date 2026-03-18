@echo off
chcp 65001 >nul
echo ============================================================
echo 启用立体声混音 (Stereo Mix)
echo ============================================================
echo.

echo 步骤 1: 打开 Windows 声音设置
echo ------------------------------------------------------------
echo 正在打开声音控制面板...
start mmsys.cpl
echo.
echo 请按以下步骤操作：
echo.
echo 1. 切换到"录制"选项卡
echo 2. 右键空白处
echo 3. 勾选"显示禁用的设备"和"显示已断开的设备"
echo 4. 找到"立体声混音"或"Stereo Mix"
echo    - 如果看到灰色/禁用的设备，那就是它
echo.
echo 完成后按任意键继续...
pause >nul

echo.
echo 步骤 2: 启用立体声混音
echo ------------------------------------------------------------
echo 1. 右键"立体声混音" → 启用
echo 2. 右键"立体声混音" → 设为默认设备
echo 3. 双击"立体声混音" → 级别 → 确保音量不是 0
echo 4. 确定
echo.
echo 完成后按任意键继续...
pause >nul

echo.
echo 步骤 3: 测试音频输入
echo ------------------------------------------------------------
echo 正在运行测试脚本...
python test_stereo_mix.py

echo.
echo 如果测试通过，按任意键继续配置...
echo 如果测试失败，请检查立体声混音是否正确启用
pause >nul

echo.
echo 步骤 4: 更新配置文件
echo ------------------------------------------------------------
echo 请手动编辑 config.yaml:
echo   audio:
echo     input_device_index: [测试通过的数字]
echo     use_microphone: false
echo.
echo 然后重启程序：
echo   python app.py
echo.

pause
