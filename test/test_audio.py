"""
音频设备测试脚本
"""
import sounddevice as sd
import numpy as np
import time

print('=' * 60)
print('音频设备完整诊断')
print('=' * 60)

# 获取所有输入设备
devices = sd.query_devices()
input_devices = []

print('\n所有输入设备：')
for i, dev in enumerate(devices):
    if dev['max_input_channels'] > 0:
        name = dev['name'][:50]
        print(f'{i}: {name} (通道:{dev["max_input_channels"]})')
        input_devices.append(i)

print(f'\n开始测试 {len(input_devices)} 个设备...\n')

working_devices = []

for device_id in input_devices:
    try:
        dev = sd.query_devices(device_id)
        channels = min(dev['max_input_channels'], 2)
        
        # 尝试录音 1 秒
        recording = sd.rec(int(1 * 16000), samplerate=16000, channels=channels, device=device_id)
        sd.wait()
        
        volume = np.max(np.abs(recording))
        name = dev['name'][:40]
        
        if volume > 0.001:
            status = 'OK'
            working_devices.append((device_id, volume, name))
        else:
            status = 'NO AUDIO'
        
        print(f'设备 {device_id:2d}: {status:8s} 音量:{volume:.6f} - {name}')
        
    except Exception as e:
        error = str(e)[:40]
        print(f'设备 {device_id:2d}: ERROR    {error} - {dev["name"][:40]}')

print('\n' + '=' * 60)
print('测试结果')
print('=' * 60)

if working_devices:
    print('\n可用的设备（按音量排序）：')
    for dev_id, vol, name in sorted(working_devices, key=lambda x: -x[1]):
        print(f'  设备 {dev_id}: 音量 {vol:.6f} - {name}')
    
    best_device = working_devices[0][0]
    print(f'\n>>> 推荐使用设备 {best_device}')
    print(f'\n在 config.yaml 中设置：')
    print(f'  audio:')
    print(f'    input_device_index: {best_device}')
else:
    print('\n没有找到可用的输入设备')
    print('请检查：')
    print('1. 是否有音频设备连接')
    print('2. 设备驱动是否已安装')
    print('3. 设备是否已启用')

print('=' * 60)
