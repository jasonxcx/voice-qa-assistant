"""
音频捕获模块 - 基于 pyaudiowpatch 的 WASAPI loopback + Faster-Whisper STT
"""
import threading
import pyaudiowpatch as pyaudio
import numpy as np
import logging
import time
from typing import Optional
from PyQt5.QtCore import pyqtSignal, QObject

from core.logger import log_system


class AudioCapture(QObject):
    """音频捕获和 STT 转换 - 使用 PyAudio + Faster-Whisper"""

    # Qt 信号
    transcription_ready = pyqtSignal(str)  # 转录文本就绪
    real_time_update = pyqtSignal(str)     # 实时转录更新
    recording_started = pyqtSignal()       # 开始录音
    recording_stopped = pyqtSignal()       # 停止录音
    error_occurred = pyqtSignal(str)       # 错误发生
    volume_update = pyqtSignal(float)      # 音量更新 (0.0 - 1.0)
    transcription_completed = pyqtSignal(str)  # 手动转录完成

    def __init__(self, config):
        super().__init__()
        self.config = config
        self.stt_model = None
        self._thread: Optional[threading.Thread] = None
        self._volume_thread: Optional[threading.Thread] = None
        self._running = False
        self._monitoring = False
        self._recording = False  # 手动控制录音状态
        self._manual_mode = False  # 手动模式：True=手动控制转录，False=自动检测
        self._audio_queue = []  # 音频缓冲区
        self._max_queue_size = 30  # 最多保存 30 秒的音频块

    def _init_stt_model(self):
        """初始化 Faster-Whisper 模型"""
        try:
            from faster_whisper import WhisperModel

            model_name = self.config.get('stt', {}).get('model', 'tiny')
            device = self.config.get('stt.local', {}).get('device', 'cpu')

            # 映射设备名称：gpu -> cuda (Faster-Whisper 使用 cuda 而不是 gpu)
            if device.lower() == 'gpu':
                device = 'cuda'

            # 根据设备选择计算类型
            if device == 'cuda':
                compute_type = 'float16'  # GPU 使用 float16 加速
            elif device == 'cpu':
                compute_type = 'float32'  # CPU 使用 float32
            else:
                compute_type = 'int8'  # 其他设备使用 int8
            
            log_system(f"加载 Faster-Whisper 模型：{model_name} (device={device}, compute_type={compute_type})", logging.INFO)
            self.stt_model = WhisperModel(
                model_size_or_path=model_name,
                device=device,
                compute_type=compute_type,
            )
            log_system("Faster-Whisper 模型加载成功", logging.INFO)

        except Exception as e:
            log_system(f"加载 STT 模型失败：{e}", logging.ERROR)
            raise

    def start_monitoring(self):
        """启动音量监控（独立于录音）"""
        if self._monitoring:
            return

        self._monitoring = True

        # 启动音量监控线程
        self._volume_thread = threading.Thread(target=self._monitor_volume, daemon=True)
        self._volume_thread.start()

    def stop_monitoring(self):
        """停止音量监控"""
        self._monitoring = False

        if self._volume_thread and self._volume_thread.is_alive():
            self._volume_thread.join(timeout=1.0)

    def start_recording(self):
        """手动模式：开始录音"""
        if self._recording:
            return
        self._recording = True
        print(f"[AudioCapture] 手动模式：开始录音 (时间: {time.strftime('%H:%M:%S')})", flush=True)
        log_system("手动模式：开始录音", logging.INFO)

    def stop_recording(self):
        """手动模式：停止录音"""
        if not self._recording:
            return
        self._recording = False
        buffer_info = "N/A"  # _audio_buffer 是 _run 中的局部变量，这里无法直接访问
        print(f"[AudioCapture] 手动模式：停止录音 (时间: {time.strftime('%H:%M:%S')}, buffer={buffer_info})", flush=True)
        log_system("手动模式：停止录音", logging.INFO)
        # 停止录音后自动触发转录
        self.transcribe_now()
        # 等待一小段时间确保转录完成
        import time
        time.sleep(0.5)
        print("[AudioCapture] 手动模式：停止录音完成", flush=True)

    def transcribe_now(self):
        """手动模式：立即转录当前缓冲区"""
        print("[AudioCapture] 手动模式：触发转录", flush=True)
        self._transcribing_manual = True

    def set_manual_mode(self, enabled: bool):
        """设置手动模式"""
        self._manual_mode = enabled
        mode_str = "手动" if enabled else "自动"
        print(f"[AudioCapture] 转录模式：{mode_str}", flush=True)
        log_system(f"转录模式：{mode_str}", logging.INFO)

    def is_recording(self) -> bool:
        """是否正在录音"""
        return self._recording

    def start(self):
        """在独立线程中启动音频捕获"""
        if self._running:
            return

        self._running = True

        # 启动录音线程
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        """运行 PyAudio 录音 + Faster-Whisper 转录"""
        try:
            # 初始化 STT 模型
            self._init_stt_model()

            # 使用 pyaudiowpatch 获取 WASAPI loopback 设备
            p = pyaudio.PyAudio()
            device_index = self._get_loopback_device(p)

            # 获取设备信息
            device_info = p.get_device_info_by_index(device_index)
            channels = min(device_info['maxInputChannels'], 2)
            sample_rate = int(device_info['defaultSampleRate'])

            p.terminate()

            log_system(f"使用 WASAPI loopback 设备：{device_index}", logging.INFO)
            print(f"[AudioCapture] 使用设备：{device_index}, 采样率：{sample_rate}, 通道：{channels}")

            # 重新创建 PyAudio 实例
            p = pyaudio.PyAudio()

            # 打开音频流
            stream = p.open(
                format=pyaudio.paInt16,
                channels=channels,
                rate=sample_rate,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=1024
            )

            log_system("开始录音循环", logging.INFO)
            print(f"[AudioCapture] 开始录音循环...", flush=True)
            self.recording_started.emit()

            # 音频缓冲区和状态
            audio_buffer = []
            silence_start = None
            speech_detected = False
            silence_threshold = 0.01  # 静音阈值 - 降低以捕获更弱的语音
            silence_duration_threshold = 1.2  # 静音持续时间（秒）后触发转录 - 降低以更快响应
            last_log_time = 0
            transcription_count = 0
            last_volume_log = 0
            min_audio_duration = 0.5  # 最小录音时长（秒）- 降低以捕获短句
            self._transcribing_manual = False  # 手动转录标志

            # 主录音循环
            while self._running:
                try:
                    # 读取音频数据
                    data = stream.read(1024, exception_on_overflow=False)
                    audio_data = np.frombuffer(data, dtype=np.int16)

                    # 计算音量（使用 RMS 更准确）
                    audio_float = audio_data.astype(np.float32) / 32768.0
                    volume = np.sqrt(np.mean(audio_float ** 2))  # RMS 音量
                    current_time = time.time()

                    # 检查是否有手动转录请求
                    if self._manual_mode and self._transcribing_manual:
                        self._transcribing_manual = False  # 重置标志
                        if len(audio_buffer) > 0:
                            # 执行转录
                            audio_duration = len(audio_buffer) / (sample_rate / 1024)
                            if audio_duration >= min_audio_duration:
                                transcription_count += 1
                                print(f"[AudioCapture] 手动转录 #{transcription_count} ({audio_duration:.1f}秒)...", flush=True)
                                # 复用自动转录的逻辑
                                # 转录在独立线程中执行，避免阻塞循环
                                args = (audio_buffer.copy(), sample_rate, 2)
                                t = threading.Thread(target=self._transcribe_buffer, args=args, daemon=True)
                                t.start()
                                audio_buffer = []  # 清空缓冲区
                        continue  # 跳过当前循环

                    # 手动模式：只在 _recording 为 True 时收集音频
                    if self._manual_mode:
                        if self._recording:
                            # 手动录音中，收集音频
                            audio_buffer.append(audio_data)
                            # 手动模式不限制缓冲区大小，记录从开始到停止的所有音频
                            # 注意：长时间录音可能导致内存占用较高
                        # 手动模式不下自动转录，由外部调用 transcribe_now() 触发
                    else:
                        # 自动模式：使用语音/静音检测
                        is_speech = volume > silence_threshold

                        if is_speech:
                            # 检测到声音，重置静音计时器
                            if not speech_detected:
                                silence_start = None
                                speech_detected = True
                                print(f"[AudioCapture] >>> 检测到语音 (volume={volume:.5f})", flush=True)
                            # 添加到缓冲区
                            audio_buffer.append(audio_data)
                            # 限制缓冲区大小（约 30 秒）
                            if len(audio_buffer) > 300:
                                audio_buffer.pop(0)
                        else:
                            # 静音
                            if speech_detected:
                                if silence_start is None:
                                    silence_start = time.time()
                                    print(f"[AudioCapture] 静音开始...", flush=True)
                                elif time.time() - silence_start > silence_duration_threshold:
                                    # 静音时间足够长，触发转录
                                    audio_duration = len(audio_buffer) / (sample_rate / 1024)  # 估算时长
                                    if audio_duration >= min_audio_duration:
                                        transcription_count += 1
                                        print(f"[AudioCapture] >>> 转录 #{transcription_count} ({audio_duration:.1f}秒)...", flush=True)

                                        self._transcribe_buffer(audio_buffer, sample_rate, channels=channels)
                                    else:
                                        print(f"[AudioCapture] 音频太短 ({audio_duration:.1f}秒 < {min_audio_duration}秒)，跳过", flush=True)

                                    # 无论是否转录，都清空缓冲区并开始新的检测
                                    audio_buffer = []
                                    speech_detected = False
                                    silence_start = None
                                    print(f"[AudioCapture] 等待音频输入...", flush=True)
                            else:
                                # 保持缓冲区有少量静音数据用于边界检测
                                if len(audio_buffer) < 50:
                                    audio_buffer.append(audio_data)

                    # 定期打印调试信息（每 10 秒）
                    if current_time - last_log_time > 10.0:
                        mode_str = "手动" if self._manual_mode else "自动"
                        rec_str = "录音中" if self._recording else "待机"
                        print(f"[AudioCapture] {mode_str}模式：{rec_str} (buffer={len(audio_buffer)}, 已转录={transcription_count})", flush=True)
                        last_log_time = current_time

                    # 定期发送音量更新
                    if self._monitoring:
                        self.volume_update.emit(min(1.0, volume * 5))

                except Exception as e:
                    log_system(f"音频读取错误：{e}", logging.WARNING)
                    time.sleep(0.1)

            # 停止时不转录剩余缓冲区以避免卡顿，并清空缓冲区
            audio_buffer = []
            stream.close()
            p.terminate()

            print(f"[AudioCapture] 录音循环结束", flush=True)
            log_system("录音循环结束", logging.INFO)
            self.recording_stopped.emit()

        except Exception as e:
            error_msg = f"音频捕获失败：{e}"
            log_system(error_msg, logging.ERROR)
            print(f"[AudioCapture] 错误：{e}")
            import traceback
            traceback.print_exc()
            self.error_occurred.emit(error_msg)

    def _transcribe_buffer(self, audio_buffer, sample_rate, channels=2, save_debug=False):
        """转录音频缓冲区"""
        try:
            if not audio_buffer or self.stt_model is None:
                return

            # 合并音频数据
            audio_data = np.concatenate(audio_buffer)

            # 转换为 float32 并归一化
            audio_float = audio_data.astype(np.float32) / 32768.0

            # 如果是立体声，转换为单声道（Whisper 需要单声道）
            if channels == 2:
                # 立体声数据：每 2 个样本是一帧，取左右声道的平均值
                num_frames = len(audio_float) // 2
                if num_frames * 2 == len(audio_float):  # 确保是偶数
                    audio_float = audio_float[:num_frames*2].reshape(-1, 2).mean(axis=1)

            # 使用 librosa 进行高质量重采样到 16kHz
            target_sample_rate = 16000
            try:
                import librosa
                audio_float = librosa.resample(audio_float, orig_sr=sample_rate, target_sr=target_sample_rate)
            except ImportError:
                # librosa 不可用时使用 numpy 插值
                num_samples = int(len(audio_float) * target_sample_rate / sample_rate)
                audio_float = np.interp(
                    np.linspace(0, len(audio_float), num_samples),
                    np.arange(len(audio_float)),
                    audio_float
                )

            audio_duration = len(audio_float) / target_sample_rate
            print(f"[AudioCapture] 正在转录 ({audio_duration:.1f}秒音频，模型={self.config.get('stt', {}).get('model', 'tiny')})...", flush=True)

            # 调试：保存音频文件
            if save_debug:
                self._save_debug_audio(audio_buffer, sample_rate, 0, "_debug", channels)

            # 转录配置 - 优化参数以提高准确率
            # 添加面试场景提示词和 IT 技术热词
            segments, info = self.stt_model.transcribe(
                audio_float,
                language='zh',
                initial_prompt="面试场景，包含技术术语如 Java, Python, MySQL, Redis, Kafka, Docker, Kubernetes, 微服务，分布式系统，算法，数据结构等。",  # 预设提示词
                hotwords="Java Python MySQL Redis Kafka Docker Kubernetes Spring TensorFlow PyTorch 微服务 分布式 算法 数据结构 多线程 并发 API SDK HTTP TCP IP",  # 技术热词
                beam_size=10,      # 增加 beam size 提高准确率
                best_of=10,        # 增加 best_of
                temperature=0.0,   # 固定温度，避免随机性
                vad_filter=False,  # 禁用 VAD，避免过滤掉有效语音
                condition_on_previous_text=True,  # 保持上下文一致性
            )

            # 收集转录结果
            text_parts = []
            for segment in segments:
                text_parts.append(segment.text.strip())
                if segment.text.strip():
                    self.real_time_update.emit(segment.text.strip())

            text = " ".join(text_parts)
            text = text.strip()

            if text:
                log_system(f"转录结果：{text}", logging.INFO)
                print(f"[AudioCapture] 转录：{text}", flush=True)
                self.transcription_ready.emit(text)
            else:
                print(f"[AudioCapture] 转录结果为空", flush=True)

        except Exception as e:
            log_system(f"转录失败：{e}", logging.WARNING)
            print(f"[AudioCapture] 转录错误：{e}", flush=True)
            import traceback
            traceback.print_exc()

    def _save_debug_audio(self, audio_buffer, sample_rate, transcription_count, suffix="", channels=2):
        """保存调试音频到 WAV 文件"""
        try:
            import wave
            import os

            # 创建调试音频目录
            debug_dir = os.path.join(os.getcwd(), 'debug_audio')
            os.makedirs(debug_dir, exist_ok=True)

            # 生成文件名
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"debug_{timestamp}_#{transcription_count}{suffix}.wav"
            filepath = os.path.join(debug_dir, filename)

            # 合并音频数据
            audio_data = np.concatenate(audio_buffer)

            # 如果是立体声，转换为单声道
            if channels == 2 and len(audio_data) % 2 == 0:
                audio_mono = audio_data.reshape(-1, 2).mean(axis=1).astype(np.int16)
            else:
                audio_mono = audio_data

            # 保存为 WAV 文件（单声道）
            with wave.open(filepath, 'wb') as wf:
                wf.setnchannels(1)  # 单声道
                wf.setsampwidth(2)  # 16-bit
                wf.setframerate(sample_rate)
                wf.writeframes(audio_mono.tobytes())


            print(f"[AudioCapture] 调试音频已保存：{filepath} (mono, {len(audio_mono)/sample_rate:.1f}秒)", flush=True)
            log_system(f"调试音频已保存：{filepath}", logging.INFO)

        except Exception as e:
            print(f"[AudioCapture] 保存调试音频失败：{e}", flush=True)

    def _get_loopback_device(self, pyaudio_instance):
        """获取 WASAPI loopback 设备索引"""
        try:
            # 1. 首先尝试使用配置的设备索引
            configured = self.config.get('audio', {}).get('input_device_index', None)
            if configured is not None:
                try:
                    info = pyaudio_instance.get_device_info_by_index(configured)
                    if info['maxInputChannels'] > 0:
                        log_system(f"使用配置的设备：{info['name']} (索引:{configured})", logging.INFO)
                        return configured
                except Exception:
                    pass

            # 2. 查找标记为 loopback 的设备
            device_count = pyaudio_instance.get_device_count()
            for i in range(device_count):
                try:
                    info = pyaudio_instance.get_device_info_by_index(i)
                    name = info['name'].lower()

                    # 查找 loopback 设备（isLoopbackDevice 标记或名称包含 Loopback）
                    is_loopback = info.get('isLoopbackDevice', False) or 'loopback' in name

                    if is_loopback and info['maxInputChannels'] > 0:
                        log_system(f"找到 Loopback 设备：{info['name']} (索引:{i})", logging.INFO)
                        return i
                except Exception:
                    pass

            # 3. 尝试使用默认的 WASAPI loopback
            try:
                loopback = pyaudio_instance.get_default_wasapi_loopback()
                log_system(f"使用默认 loopback: {loopback['name']} (索引:{loopback['index']})", logging.INFO)
                return loopback['index']
            except Exception:
                pass

            # 4. 查找 Realtek 立体声混音设备
            for i in range(device_count):
                try:
                    info = pyaudio_instance.get_device_info_by_index(i)
                    name = info['name'].lower()

                    if info['maxInputChannels'] > 0:
                        if 'realtek' in name or 'stereo mix' in name or 'mix' in name:
                            log_system(f"找到立体声混音设备：{info['name']} (索引:{i})", logging.INFO)
                            return i
                except Exception:
                    pass

        except Exception as e:
            log_system(f"无法获取音频设备：{e}", logging.WARNING)

        # 默认返回 0
        return 0

    def _monitor_volume(self):
        """监控音频音量（使用 pyaudiowpatch）"""
        try:
            p = pyaudio.PyAudio()
            device_index = self._get_loopback_device(p)

            # 获取设备信息
            device_info = p.get_device_info_by_index(device_index)
            channels = min(device_info['maxInputChannels'], 2)
            sample_rate = int(device_info['defaultSampleRate'])

            # 打开音频流
            stream = p.open(
                format=pyaudio.paInt16,
                channels=channels,
                rate=sample_rate,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=1024
            )

            log_system(f"音量监控启动：设备 {device_index}, 通道 {channels}", logging.DEBUG)

            while self._monitoring:
                try:
                    # 读取音频数据
                    data = stream.read(1024, exception_on_overflow=False)

                    # 计算音量（RMS）
                    audio_data = np.frombuffer(data, dtype=np.int16)
                    audio_float = audio_data.astype(np.float32) / 32768.0
                    volume = np.mean(np.abs(audio_float))

                    # 归一化到 0-1
                    volume = min(1.0, volume * 10)

                    # 发射音量信号
                    self.volume_update.emit(volume)

                except Exception as e:
                    # 读取失败，继续尝试
                    continue

            stream.close()
            p.terminate()

        except Exception as e:
            error_msg = f"音量监控失败：{e}"
            log_system(error_msg, logging.WARNING)
            self.volume_update.emit(0.0)

    def stop(self):
        """停止音频捕获"""
        self._running = False

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)

    def is_running(self) -> bool:
        """是否正在运行"""
        return self._running