#!/usr/bin/env python3
"""
测试音频设备选择逻辑的脚本
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.config import get_config
from core.audio_capture import AudioCapture
import pyaudiowpatch as pyaudio


def test_device_selection():
    """测试设备选择逻辑"""
    print("测试设备选择逻辑...")

    # 获取配置
    config = get_config()

    print(f"输出设备索引: {config.audio_output_device_index}")
    print(f"输入设备索引: {config.audio_input_device_index}")
    print(f"使用麦克风: {config.use_microphone}")
    print(f"默认音频设备索引: {config.audio_device_index}")

    # 创建音频捕获对象
    audio_capture = AudioCapture(config)

    # 测试设备选择逻辑
    p = pyaudio.PyAudio()
    try:
        selected_device = audio_capture._get_loopback_device(p)
        print(f"选择的设备索引: {selected_device}")

        # 获取设备信息
        device_info = p.get_device_info_by_index(selected_device)
        print(f"设备名称: {device_info['name']}")
        print(f"最大输入通道数: {device_info['maxInputChannels']}")
        print(f"默认采样率: {device_info['defaultSampleRate']}")
        print(f"Loopback设备: {device_info.get('isLoopbackDevice', False)}")
    except Exception as e:
        print(f"获取设备时出错: {e}")
    finally:
        p.terminate()


def list_all_devices():
    """列出所有音频设备"""
    print("\n所有音频设备列表:")
    p = pyaudio.PyAudio()
    try:
        device_count = p.get_device_count()
        for i in range(device_count):
            try:
                info = p.get_device_info_by_index(i)
                name = info['name']
                max_channels = info['maxInputChannels']

                is_loopback = info.get('isLoopbackDevice', False)
                is_default_output = (i == p.get_default_output_device_info()['index']) if p.get_default_output_device_info() else False

                print(f"  {i}: {name}")
                print(f"     - 输入通道: {max_channels}")
                print(f"     - Loopback: {is_loopback}")
                print(f"     - 默认输出: {is_default_output}")

                # 尝试查找可能的输出设备
                name_lower = name.lower()
                if ('output' in name_lower or 'speaker' in name_lower or 'headphone' in name_lower or
                    'stereo mix' in name_lower or 'realtek' in name_lower or 'playback' in name_lower or 'loopback' in name_lower):
                    print(f"     >>> 可能是输出设备/loopback设备 <<<")
                print()
            except Exception as e:
                print(f"  设备 {i} 获取信息失败: {e}")
    finally:
        p.terminate()


if __name__ == "__main__":
    list_all_devices()
    test_device_selection()