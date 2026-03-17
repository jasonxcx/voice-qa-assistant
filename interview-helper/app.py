"""
面试辅助工具 - 主程序入口

功能:
- 监听会议软件音频（通过 VB-Cable 系统内录）
- 实时语音转文字（Faster-Whisper GPU 加速）
- 大模型生成面试回答（支持 Qwen/Ollama）
- PyQt5 透明字幕窗口显示
"""
import sys
import asyncio
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QThread

from core.config import Config, get_config
from core.audio_capture import AudioCapture
from core.llm_client import LLMClient
from ui.overlay_window import OverlayWindow
from ui.main_window import MainWindow


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
    print("=" * 50)
    print("🎯 面试辅助工具 v1.0")
    print("=" * 50)
    
    # 加载配置
    try:
        config = get_config()
        print(f"✓ 配置文件加载成功")
        print(f"  - 大模型模式：{config.llm_mode}")
        print(f"  - STT 模型：{config.stt_model}")
        print(f"  - 音频设备索引：{config.audio_device_index}")
    except FileNotFoundError:
        print("❌ 配置文件不存在！")
        print("请检查 config.yaml 是否存在")
        sys.exit(1)
    
    # 创建 Qt 应用
    app = QApplication(sys.argv)
    app.setApplicationName("面试辅助工具")
    app.setStyle("Fusion")
    
    # 创建组件
    overlay = OverlayWindow(config)
    audio_capture = AudioCapture(config)
    llm_client = LLMClient(config)
    
    # 创建主窗口
    main_window = MainWindow(overlay, audio_capture, llm_client)
    
    # 显示窗口
    print("\n✓ 程序启动成功!")
    print("\n使用说明:")
    print("1. 在主窗口导入 Markdown 简历")
    print("2. 选择大模型模式（云端/本地）")
    print("3. 点击'开始监听'按钮")
    print("4. 字幕窗口将自动显示转录和回答")
    print("\n按 Ctrl+C 或关闭窗口退出程序\n")
    
    overlay.show()
    main_window.show()
    
    # 运行
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
