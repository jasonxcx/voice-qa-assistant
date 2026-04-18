"""
实时问答助理 - 主程序入口

功能:
- 监听会议软件音频
- 实时语音转文字（Faster-Whisper GPU 加速）
- 大模型生成回答（支持 Qwen/Ollama）
- PySide6 透明字幕窗口显示
"""

import asyncio
import sys

from PySide6.QtCore import QThread
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon

from core.audio_capture import AudioCapture
from core.config import Config, get_config
from core.llm_client import LLMClient
from ui.main_window import MainWindow
from ui.overlay_window import OverlayWindow


def create_event_loop_thread():
    """创建异步事件循环线程"""
    loop = asyncio.new_event_loop()

    def run_loop():
        loop.run_forever()

    thread = QThread()
    thread.run = run_loop
    return thread, loop


def main():
    """主函数"""
    # 设置 UTF-8 编码支持
    import os
    import traceback

    os.system("chcp 65001 >nul")  # Windows 设置 UTF-8 代码页

    print("=" * 50)
    print("[Interview Helper] 实时问答助理 v1.0")
    print("=" * 50)

    # 加载配置
    try:
        config = get_config()
        print(f"[OK] 配置文件加载成功")
        print(f"  - 大模型模式：{config.llm_mode}")
        print(f"  - STT 模型：{config.stt_model}")
        print(f"  - 音频设备索引：{config.audio_device_index}")
    except FileNotFoundError as e:
        print(f"[Error] 配置文件不存在且无法从模板创建！{e}")
        traceback.print_exc()
        sys.exit(1)
    
    # 检查是否需要配置 API Key
    if config.llm_api_key == "YOUR_DASHSCOPE_API_KEY" or config.llm_api_key == "sk-xxxxxxx":
        print("\n" + "=" * 50)
        print("[提示] 请先编辑 config.yaml 配置有效的 API Key")
        print("=" * 50)

    print("\n[1/5] 创建 Qt 应用...")
    app = QApplication(sys.argv)
    app.setApplicationName("实时问答助理")
    app.setWindowIcon(QIcon("ui/icon.ico"))
    app.setStyle("Fusion")
    print("  [OK] Qt 应用创建成功")

    print("\n[2/5] 创建字幕窗口...")
    try:
        overlay = OverlayWindow(config)
        print("  [OK] 字幕窗口创建成功")
    except Exception as e:
        print(f"  [Error] 字幕窗口创建失败：{e}")
        traceback.print_exc()
        sys.exit(1)

    print("\n[3/5] 创建音频捕获模块...")
    print("  [Info] 首次运行会下载 Whisper 模型（约 500MB-1GB），仅下载一次，后续运行会使用缓存")
    try:
        audio_capture = AudioCapture(config)
        print("  [OK] 音频捕获模块创建成功")
    except Exception as e:
        print(f"  [Error] 音频捕获模块创建失败：{e}")
        traceback.print_exc()
        sys.exit(1)

    print("\n[4/5] 创建大模型客户端...")
    try:
        llm_client = LLMClient(config)
        print("  [OK] 大模型客户端创建成功")
    except Exception as e:
        print(f"  [Error] 大模型客户端创建失败：{e}")
        traceback.print_exc()
        sys.exit(1)

    print("\n[5/5] 创建主窗口...")
    try:
        main_window = MainWindow(overlay, audio_capture, llm_client)
        print("  [OK] 主窗口创建成功")
    except Exception as e:
        print(f"  [Error] 主窗口创建失败：{e}")
        traceback.print_exc()
        sys.exit(1)

    # 显示窗口
    print("\n" + "=" * 50)
    print("[OK] 程序启动成功!")
    print("\n使用说明:")
    print("1. 在主窗口导入 Markdown 文档")
    print("2. 选择大模型模式（云端/本地）")
    print("3. 点击'开始监听'按钮")
    print("4. 字幕窗口将自动显示转录和回答")
    print("\n按 Ctrl+C 或关闭窗口退出程序")
    print("=" * 50)

    # 注意：字幕窗口在启动时不显示，点击"开始监听"后才显示
    # overlay.show()  # ← 移除这行
    main_window.show()

    # 运行
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
