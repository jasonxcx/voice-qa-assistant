"""
实时音频监控 - 测试是否有声音输入
"""
import sounddevice as sd
import numpy as np
import time
import sys

print('=' * 60)
print('实时音频监控')
print('=' * 60)
print('\n请在测试时播放影片/音乐！\n')

# 测试设备 1（Realtek 线路输入）
device_id = 1

print(f'使用设备：{device_id}')
print('监控 30 秒，按 Ctrl+C 停止...\n')

try:
    for i in range(30):
        recording = sd.rec(int(0.5 * 16000), samplerate=16000, channels=2, device=device_id)
        sd.wait()
        volume = np.max(np.abs(recording))
        
        # 简单进度条
        level = int(volume * 100)
        bar = '#' * min(level, 50)
        print(f'[{i:2d}s] 音量:{volume:.4f} |{bar:<50}| ({level}%)')
        
        time.sleep(0.5)
        
except KeyboardInterrupt:
    print('\n测试停止')
except Exception as e:
    print(f'\n错误：{e}')
    print('\n设备可能不可用，尝试其他设备...')

print('\n如果音量一直是 0%，说明：')
print('1. 没有播放声音')
print('2. 设备选择错误')
print('3. Windows 声音设置有问题')
