"""
测试转录已保存的音频文件
"""
import sys
sys.path.insert(0, 'E:/workspace/Project/interviewHelper')

from faster_whisper import WhisperModel
import wave
import numpy as np
import librosa

def test_transcribe_audio(file_path):
    """转录音频文件"""
    print(f"加载音频文件：{file_path}")

    # 读取 WAV 文件
    with wave.open(file_path, 'rb') as wf:
        n_channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        framerate = wf.getframerate()
        n_frames = wf.getnframes()

        print(f"频道：{n_channels}, 采样率：{framerate}, 时长：{n_frames/framerate:.1f}秒")

        # 读取所有帧
        raw_data = wf.readframes(n_frames)

        # 转换为 numpy 数组
        audio_data = np.frombuffer(raw_data, dtype=np.int16)

        # 转换为 float32 并归一化
        audio_float = audio_data.astype(np.float32) / 32768.0

        # 如果是立体声，转换为单声道
        if n_channels == 2:
            audio_float = audio_float.reshape(-1, 2).mean(axis=1)

        # 使用 librosa 重采样到 16kHz
        audio_float = librosa.resample(audio_float, orig_sr=framerate, target_sr=16000)

    print(f"重采样后时长：{len(audio_float) / 16000:.1f}秒")

    # 加载模型
    print("加载 Whisper 模型 (medium, cuda)...")
    model = WhisperModel('medium', device='cuda', compute_type='float16')

    print("开始转录...")
    segments, info = model.transcribe(
        audio_float,
        language='zh',
        beam_size=10,
        best_of=10,
        temperature=0.0,
        vad_filter=True,
        vad_parameters=dict(
            threshold=0.5,
            min_silence_duration_ms=500,
        ),
    )

    print(f"检测语言：{info.language}")
    print("转录结果:")

    text_parts = []
    for segment in segments:
        print(f"  [{segment.start:.1f}s - {segment.end:.1f}s]: {segment.text.strip()}")
        text_parts.append(segment.text.strip())

    text = " ".join(text_parts).strip()
    print(f"\n最终结果：{text if text else '(空)'}")


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        # 默认使用最新的调试文件
        import os
        import glob
        debug_dir = 'E:/workspace/Project/interviewHelper/debug_audio'
        files = glob.glob(os.path.join(debug_dir, '*.wav'))
        if files:
            file_path = sorted(files)[-1]
            print(f"使用最新文件：{file_path}")
        else:
            print("未找到调试音频文件")
            sys.exit(1)

    test_transcribe_audio(file_path)
