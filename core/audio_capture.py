"""
音频捕获模块 - 基于 pyaudiowpatch 的 WASAPI loopback + Faster-Whisper STT
"""
import threading
import pyaudiowpatch as pyaudio
import numpy as np
import logging
import time
import os
import re
import shutil
from pathlib import Path
from typing import Optional
from PyQt5.QtCore import pyqtSignal, QObject

from core.logger import log_system, log_stt


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
    model_loading_started = pyqtSignal()   # 模型开始加载
    model_loaded = pyqtSignal()            # 模型加载完成
    model_unloaded = pyqtSignal()          # 模型已卸载
    model_download_started = pyqtSignal(str)
    model_download_progress = pyqtSignal(float, str)
    model_download_finished = pyqtSignal()
    model_download_failed = pyqtSignal(str)

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
        self._audio_buffer = []  # 录音音频缓冲区（实例变量以便外部访问）
        self._audio_buffer_lock = threading.Lock()  # 保护 _audio_buffer 的锁

    def _init_stt_model(self):
        """初始化 Faster-Whisper 模型"""
        try:
            from faster_whisper import WhisperModel
            from huggingface_hub import snapshot_download
            from tqdm.auto import tqdm as _tqdm

            model_name = self.config.get("stt.model", "tiny")
            device = self.config.get("stt.local.device", "cpu")
            download_mirror = (self.config.get("stt.download.mirror", "") or "").strip()
            local_model_path = (self.config.get("stt.local.model_path", "") or "").strip()
            cache_dir = (self.config.get("stt.download.cache_dir", "") or "").strip() or None

            if device.lower() == "gpu":
                device = "cuda"

            if device == "cuda":
                compute_type = "float16"
            elif device == "cpu":
                compute_type = "float32"
            else:
                compute_type = "int8"

            log_system(f"加载 Faster-Whisper 模型：{model_name} (device={device}, compute_type={compute_type})", logging.INFO)
            self.model_loading_started.emit()

            model_source = model_name
            if local_model_path:
                model_source = local_model_path
            else:
                repo_map = {
                    "tiny": "Systran/faster-whisper-tiny",
                    "base": "Systran/faster-whisper-base",
                    "small": "Systran/faster-whisper-small",
                    "medium": "Systran/faster-whisper-medium",
                    "large-v1": "Systran/faster-whisper-large-v1",
                    "large-v2": "Systran/faster-whisper-large-v2",
                    "large-v3": "Systran/faster-whisper-large-v3",
                    "large": "Systran/faster-whisper-large-v3",
                }
                repo_id = repo_map.get((model_name or "").strip().lower())
                if repo_id:
                    self._cancel_download = False
                    self.model_download_started.emit(repo_id)
                    start_ts = time.time()

                    class SignalTqdm(_tqdm):
                        def update(inner_self, n=1):
                            if self._cancel_download:
                                raise RuntimeError("用户取消下载")
                            super().update(n)
                            done = int(inner_self.n or 0)
                            total = int(inner_self.total or 0)
                            progress = (done * 100.0 / total) if total > 0 else 0.0
                            elapsed = max(1e-6, time.time() - start_ts)
                            speed = done / elapsed
                            self.model_download_progress.emit(min(100.0, progress), f"{done}/{max(total,1)} files, {speed:.2f} files/s")

                    download_kwargs = {
                        "repo_id": repo_id,
                        "local_dir": cache_dir,
                        "resume_download": True,
                        "tqdm_class": SignalTqdm,
                    }
                    if download_mirror:
                        endpoint = download_mirror.rstrip("/")
                        download_kwargs["endpoint"] = endpoint
                        log_system(f"STT 下载镜像生效：{endpoint}", logging.INFO)

                    model_source = snapshot_download(**download_kwargs)
                    model_bin = Path(model_source) / "model.bin"
                    if not model_bin.exists():
                        raise RuntimeError(f"模型下载不完整：{model_source} 缺少 model.bin")
                    self.model_download_progress.emit(100.0, "完成")
                    self.model_download_finished.emit()

            self.stt_model = WhisperModel(
                model_size_or_path=model_source,
                device=device,
                compute_type=compute_type,
            )
            log_system("Faster-Whisper 模型加载成功", logging.INFO)
            self.model_loaded.emit()

        except Exception as e:
            self.model_download_failed.emit(str(e))
            log_system(f"加载 STT 模型失败：{e}", logging.ERROR)
            raise

    @staticmethod
    def _extract_bad_snapshot_path(error_text: str) -> Optional[str]:
        match = re.search(r"model '([^']+)'", error_text or "")
        return match.group(1) if match else None

    @staticmethod
    def _remove_bad_snapshot(snapshot_path: str):
        try:
            shutil.rmtree(snapshot_path, ignore_errors=True)
        except Exception:
            pass

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

    def stop_recording(self):
        """手动模式：停止录音并触发转录"""
        if not self._recording:
            print(f"[AudioCapture] stop_recording: _recording=False, 直接返回", flush=True)
            return
        self._recording = False
        log_system(f"手动模式：停止录音 (时间: {time.strftime('%H:%M:%S')})", logging.INFO)
        # 立即触发转录（在独立线程中执行，避免阻塞主线程）
        with self._audio_buffer_lock:
            if self._audio_buffer:
                # 设置转录已触发标记，防止 _run() 线程重复触发
                self._transcription_triggered = True
                buffer_copy = self._audio_buffer.copy()
                self._audio_buffer = []  # 清空缓冲区，避免重复处理
                sample_rate = getattr(self, '_sample_rate', 16000)
                channels = getattr(self, '_channels', 2)
                print(f"[AudioCapture] 手动模式：触发转录 (在线程中) buffer_copy 长度: {len(buffer_copy)}, stt_model: {self.stt_model}", flush=True)
                # 在独立线程中执行转录，避免阻塞主线程
                threading.Thread(
                    target=self._transcribe_buffer,
                    args=(buffer_copy, sample_rate, channels),
                    daemon=True
                ).start()
            else:
                print(f"[AudioCapture] stop_recording: _audio_buffer 为空，不触发转录", flush=True)

    def set_manual_mode(self, enabled: bool):
        """设置手动模式"""
        self._manual_mode = enabled
        mode_str = "手动" if enabled else "自动"
        print(f"[AudioCapture] 转录模式：{mode_str}", flush=True)
        log_system(f"转录模式：{mode_str}", logging.INFO)

    def is_recording(self) -> bool:
        """是否正在录音"""
        return self._recording

    def is_model_loaded(self) -> bool:
        """检查模型是否已加载"""
        return self.stt_model is not None

    def start(self):
        """在独立线程中启动音频捕获"""
        if self._running:
            print("[AudioCapture] 已在运行，跳过启动", flush=True)
            return
        self._running = True
        # 启动录音线程
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        """运行 PyAudio 录音 + Faster-Whisper 转录"""
        try:
            # 初始化 STT 模型
            print("[AudioCapture] 初始化 STT 模型...", flush=True)
            self._init_stt_model()
            print("[AudioCapture] STT 模型初始化完成", flush=True)

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

            log_system("已打开音频流...", logging.INFO)
            self.recording_started.emit()

            # 保存音频参数作为实例变量，供 stop_recording 使用
            self._sample_rate = sample_rate
            self._channels = channels

            # 使用实例变量以便在 stop_recording 中访问
            self._audio_buffer = []
            # 标记转录是否已触发，避免重复转录
            self._transcription_triggered = False

            # 主录音循环
            while self._running:
                try:
                    # 读取音频数据
                    data = stream.read(1024, exception_on_overflow=False)
                    audio_data = np.frombuffer(data, dtype=np.int16)

                    # 计算音量（使用 RMS 更准确）
                    audio_float = audio_data.astype(np.float32) / 32768.0
                    volume = np.sqrt(np.mean(audio_float ** 2))  # RMS 音量

                    # 手动模式：只在 _recording 为 True 时收集音频
                    if self._manual_mode:
                        if self._recording:
                            # 手动录音中，收集音频
                            with self._audio_buffer_lock:
                                self._audio_buffer.append(audio_data)
                            # 手动模式不限制缓冲区大小，记录从开始到停止的所有音频
                            # 注意：长时间录音可能导致内存占用较高
                    else:
                        # 自动模式：始终收集音频
                        with self._audio_buffer_lock:
                            self._audio_buffer.append(audio_data)

                    # 始终发送音量更新（只要在运行中）
                    self.volume_update.emit(min(1.0, volume * 5))

                except Exception as e:
                    log_system(f"音频读取错误：{e}", logging.WARNING)
                    time.sleep(0.1)

                # 每次迭代检查是否停止了录音（手动模式）
                if self._manual_mode and not self._recording:
                    # 停止录音后触发转录（只在第一次循环时触发）
                    with self._audio_buffer_lock:
                        if not hasattr(self, '_transcription_triggered') and self._audio_buffer:
                            self._transcription_triggered = True
                            sample_rate = getattr(self, '_sample_rate', 16000)
                            channels = getattr(self, '_channels', 2)
                            buffer_copy = self._audio_buffer.copy()
                            self._audio_buffer = []  # 清空缓冲区
                            print(f"[AudioCapture] 手动模式：循环检测到停止，触发转录 (在线程中)", flush=True)
                            # 在独立线程中执行转录，避免阻塞主线程
                            threading.Thread(
                                target=self._transcribe_buffer,
                                args=(buffer_copy, sample_rate, channels),
                                daemon=True
                            ).start()

            # 如果循环结束时还在录音，转录剩余缓冲区
            with self._audio_buffer_lock:
                if self._audio_buffer:
                    sample_rate = getattr(self, '_sample_rate', 16000)
                    channels = getattr(self, '_channels', 2)
                    buffer_copy = self._audio_buffer.copy()
                    print(f"[AudioCapture] 录音循环结束，转录剩余缓冲区 (在线程中)", flush=True)
                    # 在独立线程中执行转录，避免阻塞主线程
                    threading.Thread(
                        target=self._transcribe_buffer,
                        args=(buffer_copy, sample_rate, channels),
                        daemon=True
                    ).start()
                self._audio_buffer = []  # 清空缓冲区

            log_system("录音循环结束", logging.INFO)
            self.recording_stopped.emit()

        except Exception as e:
            error_msg = f"音频捕获失败：{e}"
            log_system(error_msg, logging.ERROR)
            print(f"[AudioCapture] 错误：{e}")
            import traceback
            traceback.print_exc()
            self.error_occurred.emit(error_msg)

    def _transcribe_current_buffer(self, sample_rate, channels=2):
        """转录当前音频缓冲区（实例变量）"""
        with self._audio_buffer_lock:
            if not self._audio_buffer or self.stt_model is None:
                return
            # 复制缓冲区数据，避免与 _run 线程同时访问
            buffer_copy = self._audio_buffer.copy()
            self._audio_buffer = []  # 清空缓冲区
            # 在独立线程中执行转录，避免阻塞主线程
            threading.Thread(
                target=self._transcribe_buffer,
                args=(buffer_copy, sample_rate, channels),
                daemon=True
            ).start()

    def _transcribe_buffer(self, audio_buffer, sample_rate, channels=2, save_debug=False):
        """转录音频缓冲区"""
        try:
            print(f"[AudioCapture] _transcribe_buffer: audio_buffer长度={len(audio_buffer) if audio_buffer else 0}, stt_model={self.stt_model}", flush=True)
            if not audio_buffer or self.stt_model is None:
                print(f"[AudioCapture] _transcribe_buffer: 退出 - audio_buffer={audio_buffer is not None}, stt_model={self.stt_model}", flush=True)
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
                log_stt(f"转录结果：{text}")
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
        print("[AudioCapture] 正在停止音频捕获...", flush=True)
        log_system("正在停止音频捕获...", logging.INFO)
        self._running = False
        # 清理转录触发标记
        if hasattr(self, '_transcription_triggered'):
            delattr(self, '_transcription_triggered')

        # 停止音量监控
        self.stop_monitoring()

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)

        # 卸载 STT 模型以释放内存
        if self.stt_model is not None:
            print("[AudioCapture] 正在卸载 STT 模型...", flush=True)
            log_system("正在卸载 STT 模型...", logging.INFO)
            self.stt_model = None
            print("[AudioCapture] STT 模型已卸载", flush=True)
            log_system("STT 模型已卸载", logging.INFO)
            self.model_unloaded.emit()

        print("[AudioCapture] 音频捕获已停止", flush=True)
        log_system("音频捕获已停止", logging.INFO)

    def is_running(self) -> bool:
        """是否正在运行"""
        return self._running

    def request_cancel_download(self):
        """请求取消模型下载"""
        self._cancel_download = True
