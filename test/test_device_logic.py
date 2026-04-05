"""
验证音频设备切换逻辑的测试程序
"""
import sys
import os

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from core.config import get_config
from core.audio_player import AudioPlayer


def test_device_types_and_usage():
    """测试设备类型和用途"""
    print("=" * 60)
    print("音频设备类型和用途验证")
    print("=" * 60)

    # 获取配置和音频播放器
    config = get_config()
    player = AudioPlayer()

    print(f"当前输入设备索引: {config.audio_device_index}")
    print(f"当前输出设备索引: {config.audio_output_device_index}")

    # 列出所有设备及类型
    print("\n系统中所有音频设备及其类型:")
    devices = player.list_output_devices() + player.list_input_devices()

    # 去重并整理
    all_devices = {}
    input_devices = player.list_input_devices()
    output_devices = player.list_output_devices()

    # 先添加输入设备
    for dev in input_devices:
        idx = dev['index']
        all_devices[idx] = {
            'name': dev['name'],
            'input_channels': dev['max_input_channels'],
            'output_channels': 0,
            'type': 'input'
        }

    # 再处理输出设备，标记双工设备
    for dev in output_devices:
        idx = dev['index']
        if idx in all_devices:
            # 这是一个既有输入又有输出的设备
            all_devices[idx]['output_channels'] = dev['max_output_channels']
            all_devices[idx]['type'] = 'input_output'
        else:
            # 纯输出设备
            all_devices[idx] = {
                'name': dev['name'],
                'input_channels': 0,
                'output_channels': dev['max_output_channels'],
                'type': 'output'
            }

    # 显示所有设备
    for idx in sorted(all_devices.keys()):
        dev = all_devices[idx]
        type_desc = {
            'input': '[输入]',
            'output': '[输出]',
            'input_output': '[输入/输出]'
        }[dev['type']]

        print(f"  [{idx:2d}] {dev['name']:<50} {type_desc}")
        print(f"       输入通道: {dev['input_channels']:2d}, 输出通道: {dev['output_channels']:2d}")

    print("\n" + "=" * 60)
    print("设备用途说明:")
    print("- 输入设备([输入], [输入/输出]): 用于录音和音量监控(STT)")
    print("- 输出设备([输出], [输入/输出]): 用于音频播放(TTS等)")
    print("- 当前配置:")
    print(f"  - 音频输入设备: {config.audio_device_index} (用于STT)")
    print(f"  - 音频输出设备: {config.audio_output_device_index} (用于播放)")
    print("=" * 60)


if __name__ == "__main__":
    test_device_types_and_usage()