"""
分析音频文件的音量特征
"""
import wave
import numpy as np
import librosa
import os
import glob

def analyze_audio(file_path):
    """分析音频文件"""
    print(f"分析文件：{file_path}")

    # 读取 WAV 文件
    with wave.open(file_path, 'rb') as wf:
        n_channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        framerate = wf.getframerate()
        n_frames = wf.getnframes()

        print(f"频道：{n_channels}, 采样率：{framerate}, 总帧数：{n_frames}")
        print(f"时长：{n_frames/framerate:.2f}秒")

        # 读取所有帧
        raw_data = wf.readframes(n_frames)

        # 转换为 numpy 数组
        audio_data = np.frombuffer(raw_data, dtype=np.int16)

        # 如果是立体声，转换为单声道
        if n_channels == 2:
            audio_float = audio_data.reshape(-1, 2).mean(axis=1)
        else:
            audio_float = audio_data.astype(np.float32)

        # 归一化
        audio_float = audio_float / 32768.0

        # 分析音量
        print(f"\n音频数据统计:")
        print(f"  最小值：{audio_float.min():.5f}")
        print(f"  最大值：{audio_float.max():.5f}")
        print(f"  平均值：{audio_float.mean():.5f}")
        print(f"  RMS (整体音量): {np.sqrt(np.mean(audio_float ** 2)):.5f}")

        # 打印每秒的音量
        samples_per_second = framerate // n_channels if n_channels == 2 else framerate
        duration = len(audio_float) / framerate
        print(f"\n每秒音量分析:")

        for i in range(int(duration) + 1):
            start = int(i * framerate)
            end = min(int((i + 1) * framerate), len(audio_float))
            chunk = audio_float[start:end]
            if len(chunk) > 0:
                rms = np.sqrt(np.mean(chunk ** 2))
                max_val = np.max(np.abs(chunk))
                print(f"  {i}-{i+1}秒：RMS={rms:.5f}, Max={max_val:.5f}")

        # 重采样到 16kHz 后再分析
        print("\n重采样到 16kHz 后:")
        audio_resampled = librosa.resample(audio_float, orig_sr=framerate, target_sr=16000)
        print(f"  重采样后样本数：{len(audio_resampled)}")
        print(f"  重采样后时长：{len(audio_resampled) / 16000:.2f}秒")
        print(f"  RMS: {np.sqrt(np.mean(audio_resampled ** 2)):.5f}")
        print(f"  Max: {np.max(np.abs(audio_resampled)):.5f}")

        # 检测静音段
        print("\n静音检测 (RMS < 0.01):")
        chunk_size = 16000  # 1 秒
        for i in range(0, len(audio_resampled), chunk_size):
            chunk = audio_resampled[i:i+chunk_size]
            if len(chunk) > 0:
                rms = np.sqrt(np.mean(chunk ** 2))
                is_silent = rms < 0.01
                print(f"  {i/16000:.1f}s: RMS={rms:.5f} {'[静音]' if is_silent else '[有声]'}")


if __name__ == '__main__':
    debug_dir = 'E:/workspace/Project/interviewHelper/debug_audio'
    files = glob.glob(os.path.join(debug_dir, '*.wav'))
    if files:
        file_path = sorted(files)[-1]
        analyze_audio(file_path)
    else:
        print("未找到调试音频文件")
