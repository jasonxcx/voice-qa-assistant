"""
测试音频捕获和转录
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pyaudiowpatch as pyaudio
from core.config import Config
from faster_whisper import WhisperModel


def test_audio_capture():
    """测试音频捕获并保存为 WAV 文件"""
    config = Config()
    device_index = config.get('audio', {}).get('input_device_index', 9)

    p = pyaudio.PyAudio()

    # 获取设备信息
    device_info = p.get_device_info_by_index(device_index)
    channels = min(device_info['maxInputChannels'], 2)
    sample_rate = int(device_info['defaultSampleRate'])

    print(f"使用设备：{device_info['name']}")
    print(f"采样率：{sample_rate}, 通道：{channels}")

    # 打开音频流
    stream = p.open(
        format=pyaudio.paInt16,
        channels=channels,
        rate=sample_rate,
        input=True,
        input_device_index=device_index,
        frames_per_buffer=1024
    )

    print("开始录音 10 秒...")
    audio_buffer = []

    # 录制 10 秒
    for i in range(100):  # 100 * 1024 frames ≈ 10 秒
        data = stream.read(1024, exception_on_overflow=False)
        audio_buffer.append(data)

        # 计算音量
        audio_data = np.frombuffer(data, dtype=np.int16)
        audio_float = audio_data.astype(np.float32) / 32768.0
        volume = np.sqrt(np.mean(audio_float ** 2))

        if i % 10 == 0:
            print(f"  第 {i//10} 秒，音量：{volume:.5f}")

    stream.close()
    p.terminate()

    # 保存为 WAV 文件
    import wave
    output_path = os.path.join(os.path.dirname(__file__), 'test_output.wav')
    print(f"保存音频到：{output_path}")

    with wave.open(output_path, 'wb') as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        wf.writeframes(b''.join(audio_buffer))

    print(f"音频已保存，总帧数：{len(audio_buffer)}")

    # 测试转录
    print("\n开始转录测试...")
    model = WhisperModel('tiny', device='cpu', compute_type='float32')

    # 读取 WAV 文件
    with wave.open(output_path, 'rb') as wf:
        n_channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        framerate = wf.getframerate()
        n_frames = wf.getnframes()

        # 读取所有帧
        raw_data = wf.readframes(n_frames)

        # 转换为 numpy 数组
        audio_data = np.frombuffer(raw_data, dtype=np.int16)

        # 转换为 float32 并归一化
        audio_float = audio_data.astype(np.float32) / 32768.0

        # 如果是立体声，转换为单声道
        if n_channels == 2:
            audio_float = audio_float.reshape(-1, 2).mean(axis=1)

        # 重采样到 16kHz
        target_sample_rate = 16000
        if framerate != target_sample_rate:
            num_samples = int(len(audio_float) * target_sample_rate / framerate)
            audio_float = np.interp(
                np.linspace(0, len(audio_float), num_samples),
                np.arange(len(audio_float)),
                audio_float
            ).astype(np.float32)

    print(f"音频时长：{len(audio_float) / target_sample_rate:.1f}秒")
    print("正在转录...")

    segments, info = model.transcribe(
        audio_float,
        language='zh',
        beam_size=5,
        best_of=5,
        temperature=0.0,
        vad_filter=False,
    )

    text_parts = []
    for segment in segments:
        text_parts.append(segment.text.strip())
        print(f"  片段：{segment.text.strip()}")

    text = " ".join(text_parts).strip()
    print(f"\n转录结果：{text if text else '(空)'}")


if __name__ == '__main__':
    test_audio_capture()
