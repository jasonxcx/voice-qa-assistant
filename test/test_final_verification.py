#!/usr/bin/env python3
"""
验证音频设备切换功能的测试脚本
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.config import get_config
from core.audio_capture import AudioCapture
import pyaudiowpatch as pyaudio


def test_final_configuration():
    """最终配置验证测试"""
    print("=" * 60)
    print("最终配置验证测试")
    print("=" * 60)

    # 获取配置
    config = get_config()

    print(f"当前配置:")
    print(f"  - use_microphone: {config.use_microphone}")
    print(f"  - input_device_index: {config.audio_input_device_index}")
    print(f"  - output_device_index: {config.audio_output_device_index}")
    print(f"  - effective audio_device_index: {config.audio_device_index}")

    # 创建音频捕获对象并测试设备选择
    audio_capture = AudioCapture(config)

    p = pyaudio.PyAudio()
    try:
        selected_device = audio_capture._get_loopback_device(p)
        device_info = p.get_device_info_by_index(selected_device)

        print(f"\n设备选择结果:")
        print(f"  - 选中设备索引: {selected_device}")
        print(f"  - 设备名称: {device_info['name']}")
        print(f"  - 最大输入通道: {device_info['maxInputChannels']}")
        print(f"  - 是否为Loopback: {device_info.get('isLoopbackDevice', False)}")
        print(f"  - 默认采样率: {device_info['defaultSampleRate']}")

        # 判断是否为理想的设备
        is_loopback = device_info.get('isLoopbackDevice', False)
        has_input_channels = device_info['maxInputChannels'] > 0

        if is_loopback and has_input_channels:
            print(f"\n[V] SUCCESS: 选择了理想的Loopback设备！")
            print(f"   - 设备可以监听系统音频输出")
            print(f"   - 不会与麦克风在视频会议中产生冲突")
        elif has_input_channels and not is_loopback:
            print(f"\n[W] WARNING: 选择了普通输入设备")
            print(f"   - 建议启用loopback模式以避免麦克风冲突")
        else:
            print(f"\n[X] ERROR: 选择了无效设备")
            print(f"   - 设备无输入通道，无法捕获音频")

    except Exception as e:
        print(f"❌ ERROR: 获取设备时出错: {e}")
    finally:
        p.terminate()

    print("\n" + "=" * 60)


def simulate_ui_device_switch():
    """模拟UI设备切换测试"""
    print("模拟UI设备切换测试")
    print("-" * 30)

    config = get_config()

    # 保存原始配置
    original_use_mic = config.get("audio.use_microphone", False)
    original_input_idx = config.get("audio.input_device_index", 0)
    original_output_idx = config.get("audio.output_device_index", 1)

    print(f"原始配置 - use_microphone: {original_use_mic}")

    # 模拟切换到麦克风模式
    print("\n1. 切换到麦克风模式:")
    config.set("audio.use_microphone", True)
    mic_device_idx = config.audio_device_index
    print(f"   - use_microphone 设置为 True")
    print(f"   - 有效设备索引: {mic_device_idx} (应为input_device_index)")

    # 模拟切换回扬声器模式
    print("\n2. 切换回扬声器监听模式:")
    config.set("audio.use_microphone", False)
    speaker_device_idx = config.audio_device_index
    print(f"   - use_microphone 设置为 False")
    print(f"   - 有效设备索引: {speaker_device_idx} (应为output_device_index)")

    # 恢复原始配置
    config.set("audio.use_microphone", original_use_mic)
    config.set("audio.input_device_index", original_input_idx)
    config.set("audio.output_device_index", original_output_idx)

    print(f"\n3. 已恢复原始配置")


if __name__ == "__main__":
    test_final_configuration()
    simulate_ui_device_switch()