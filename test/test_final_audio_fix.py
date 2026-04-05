"""
最终集成测试 - 验证音频设备监听修复
"""
import sys
import os

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

import pyaudiowpatch as pyaudio
from core.config import get_config
from core.audio_capture import AudioCapture


def test_final_integration():
    """最终集成测试"""
    print("=" * 60)
    print("最终集成测试 - 音频设备监听修复验证")
    print("=" * 60)

    # 获取配置
    config = get_config()
    print(f"配置状态:")
    print(f"  use_microphone: {config.use_microphone}")
    print(f"  input_device_index: {config.audio_input_device_index}")
    print(f"  output_device_index: {config.audio_output_device_index}")

    # 创建音频捕获实例
    audio_capture = AudioCapture(config)

    # 测试设备选择
    p = pyaudio.PyAudio()
    try:
        selected_device_index = audio_capture._get_loopback_device(p)
        device_info = p.get_device_info_by_index(selected_device_index)

        print(f"\n设备选择结果:")
        print(f"  选中设备索引: {selected_device_index}")
        print(f"  设备名称: {device_info['name']}")
        print(f"  输入通道数: {device_info['maxInputChannels']}")
        print(f"  是否为Loopback: {device_info.get('isLoopbackDevice', False)}")

        # 验证选择是否正确
        if config.use_microphone:
            # 应该选择输入设备
            if device_info['maxInputChannels'] > 0:
                print("  [OK] 正确选择了输入设备（麦克风模式）")
            else:
                print("  [ERROR] 错误：麦克风模式下未选择有效的输入设备")
        else:
            # 应该选择Loopback或混音设备
            is_loopback = (device_info.get('isLoopbackDevice', False) or
                          'loopback' in device_info['name'].lower() or
                          'mix' in device_info['name'].lower() or
                          'stereo mix' in device_info['name'].lower())

            if is_loopback and device_info['maxInputChannels'] > 0:
                print("  [OK] 正确选择了Loopback/混音设备（输出监听模式）")
            else:
                print("  [WARNING] 警告：可能未选择最佳的Loopback设备")

        # 尝试打开音频流进行实际测试
        try:
            stream = p.open(
                format=pyaudio.paInt16,
                channels=min(device_info['maxInputChannels'], 2),
                rate=int(device_info['defaultSampleRate']),
                input=True,
                input_device_index=selected_device_index,
                frames_per_buffer=1024
            )
            stream.close()
            print("  [OK] 成功打开音频流")
        except Exception as e:
            print(f"  ✗ 打开音频流失败: {e}")

    except Exception as e:
        print(f"设备选择测试失败: {e}")
    finally:
        p.terminate()

    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    test_final_integration()