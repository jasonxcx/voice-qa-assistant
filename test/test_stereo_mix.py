"""
测试立体声混音设备
"""
import sounddevice as sd
import numpy as np
import time

print('=' * 60)
print('测试立体声混音设备')
print('=' * 60)
print()
print('正在播放影片的情况下测试...\n')

# 测试所有输入设备
devices = sd.query_devices()
working_devices = []

for i, dev in enumerate(devices):
    if dev['max_input_channels'] <= 0:
        continue
    
    name = dev['name'][:40]
    
    # 只测试 Realtek 相关设备
    if 'realtek' not in name.lower() and 'microsoft' not in name.lower():
        continue
    
    print(f'测试设备 {i}: {name}...', end=' ')
    
    try:
        # 尝试录音 1 秒
        channels = min(dev['max_input_channels'], 2)
        samplerate = int(dev['default_samplerate'])
        
        recording = sd.rec(int(1 * 16000), samplerate=16000, channels=channels, device=i)
        sd.wait()
        
        volume = np.max(np.abs(recording))
        
        if volume > 0.001:
            print(f'OK (音量:{volume:.4f})')
            working_devices.append((i, volume, name))
        else:
            print(f'无声 (音量:{volume:.4f})')
            
    except Exception as e:
        print(f'错误：{str(e)[:30]}')

print()
print('=' * 60)
print('测试结果')
print('=' * 60)

if working_devices:
    print('\n可用的设备（按音量排序）：')
    for dev_id, vol, name in sorted(working_devices, key=lambda x: -x[1]):
        print(f'  设备 {dev_id}: 音量 {vol:.4f} - {name}')
    
    best = working_devices[0]
    print(f'\n>>> 使用设备 {best[0]}')
    print(f'\n请运行：')
    print(f'  在 config.yaml 中设置 input_device_index: {best[0]}')
else:
    print('\n未找到可用的立体声混音设备')
    print('请检查：')
    print('1. 右键喇叭 → 声音 → 录制')
    print('2. 找到"立体声混音" → 右键启用 → 设为默认')
    print('3. 播放影片/音乐')
    print('4. 重新运行测试')

print('=' * 60)
