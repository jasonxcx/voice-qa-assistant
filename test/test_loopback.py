"""
测试 WASAPI loopback 设备
"""
import pyaudiowpatch as pyaudio
import numpy as np

p = pyaudio.PyAudio()

print("=" * 60)
print("WASAPI Loopback 音频测试")
print("=" * 60)

# 获取默认 loopback
try:
    loopback = p.get_default_wasapi_loopback()
    print(f"\n默认 WASAPI Loopback 设备:")
    print(f"  名称：{loopback['name']}")
    print(f"  索引：{loopback['index']}")
    print(f"  采样率：{loopback['defaultSampleRate']}")
    device_index = loopback['index']
except Exception as e:
    print(f"\n无法获取默认 loopback: {e}")
    device_index = 9
    print(f"使用备用设备索引：{device_index}")

dev = p.get_device_info_by_index(device_index)
print(f"\n设备详情:")
print(f"  名称：{dev['name']}")
print(f"  输入通道：{dev['maxInputChannels']}")
print(f"  是否 Loopback: {dev.get('isLoopbackDevice', False)}")

print("\n" + "=" * 60)
print("正在录音 5 秒... 请播放声音!")
print("=" * 60)

stream = p.open(
    format=pyaudio.paInt16,
    channels=min(dev['maxInputChannels'], 2),
    rate=int(dev['defaultSampleRate']),
    input=True,
    input_device_index=device_index,
    frames_per_buffer=1024
)

print("录音中...")
max_volume = 0
volumes = []

for i in range(50):  # 5 秒
    try:
        data = stream.read(1024, exception_on_overflow=False)
        audio_data = np.frombuffer(data, dtype=np.int16)
        volume = np.max(np.abs(audio_data.astype(np.float32) / 32768.0))
        max_volume = max(max_volume, volume)
        volumes.append(volume)
        if volume > 0.01:
            print(f'  [{i*0.1:.1f}s] 检测到声音：{volume:.4f}')
    except Exception as e:
        print(f'读取错误：{e}')
        break

stream.close()
p.terminate()

avg_volume = np.mean(volumes) if volumes else 0

print("\n" + "=" * 60)
print(f"测试结果:")
print(f"  最大音量：{max_volume:.4f}")
print(f"  平均音量：{avg_volume:.4f}")

if max_volume > 0.01:
    print(f"\n设备可用！请在 config.yaml 中设置:")
    print(f"  audio.input_device_index: {device_index}")
else:
    print("\n没有检测到声音")
    print("请检查:")
    print("  1. 是否正在播放声音")
    print("  2. Windows 音量合成器中该设备未被静音")
print("=" * 60)
