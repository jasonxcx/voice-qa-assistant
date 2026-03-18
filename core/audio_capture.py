"""
音频捕获模块 - 基于 pyaudiowpatch 的 WASAPI loopback
参考：https://github.com/SMACY2017/InterPilot/blob/main/src/audio_capture.py
"""
import threading
import pyaudiowpatch as pyaudio
import numpy as np
import logging
from typing import Optional
from PyQt5.QtCore import pyqtSignal, QObject

from core.logger import log_system


class AudioCapture(QObject):
    """音频捕获和 STT 转换"""
    
    # Qt 信号
    transcription_ready = pyqtSignal(str)  # 转录文本就绪
    real_time_update = pyqtSignal(str)     # 实时转录更新
    recording_started = pyqtSignal()       # 开始录音
    recording_stopped = pyqtSignal()       # 停止录音
    error_occurred = pyqtSignal(str)       # 错误发生
    volume_update = pyqtSignal(float)      # 音量更新 (0.0 - 1.0)
    
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.recorder = None
        self._thread: Optional[threading.Thread] = None
        self._volume_thread: Optional[threading.Thread] = None
        self._running = False
        self._monitoring = False
    
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
    
    def start(self):
        """在独立线程中启动音频捕获"""
        if self._running:
            return
        
        self._running = True
        
        # 启动录音线程
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
    
    def _run(self):
        """运行 RealtimeSTT 录音循环"""
        try:
            from RealtimeSTT import AudioToTextRecorder
            
            # 使用 pyaudiowpatch 获取 WASAPI loopback 设备
            p = pyaudio.PyAudio()
            device_index = self._get_loopback_device(p)
            p.terminate()
            
            log_system(f"使用 WASAPI loopback 设备：{device_index}", logging.INFO)
            print(f"[AudioCapture] 使用设备：{device_index}")
            
            # 配置 RealtimeSTT - 使用最简配置
            log_system("初始化 RealtimeSTT...", logging.INFO)
            print(f"[AudioCapture] 初始化 RealtimeSTT...", flush=True)
            
            # 使用 loopback 模式捕获系统音频
            log_system("使用 loopback 模式捕获系统音频", logging.INFO)
            print(f"[AudioCapture] 使用 loopback 模式", flush=True)
            
            self.recorder = AudioToTextRecorder(
                model="tiny",
                language="zh",
                input_device_index=device_index,
                use_microphone=False,
                enable_realtime_transcription=True,
                on_realtime_transcription_update=self._on_realtime_update,
                on_recording_start=self._on_recording_start,
                on_recording_stop=self._on_recording_stop,
                spinner=True,
                level=10,
                # 静音检测
                silero_sensitivity=0.4,
                webrtc_sensitivity=3,
                post_speech_silence_duration=1.0,
                min_gap_between_recordings=0.1,
                # 音频处理
                normalize_audio=True,
                # 调试
                use_extended_logging=True,
            )
            
            log_system("RealtimeSTT 初始化成功", logging.INFO)
            print(f"[AudioCapture] RealtimeSTT 初始化成功", flush=True)
            
            log_system("RealtimeSTT 初始化成功", logging.INFO)
            print(f"[AudioCapture] RealtimeSTT 初始化成功")
            self.recording_started.emit()
            
            # 主录音循环
            log_system("开始录音循环", logging.INFO)
            print(f"[AudioCapture] 开始录音循环...")
            
            import sys
            while self._running:
                def process_text(text):
                    """转录完成回调"""
                    log_system(f"转录文本：{text[:50]}", logging.DEBUG)
                    print(f"[AudioCapture] 转录：{text}", flush=True)
                    if text.strip():
                        self.transcription_ready.emit(text)
                
                try:
                    # 使用 realtime 模式持续监听
                    print(f"[AudioCapture] 等待音频输入...", flush=True)
                    
                    # 使用 text() 方法，它会阻塞直到检测到语音
                    text = self.recorder.text(process_text)
                    
                    print(f"[AudioCapture] 收到文本：{text}", flush=True)
                    if text:
                        log_system(f"收到转录：{text[:100]}", logging.INFO)
                        
                except Exception as e:
                    log_system(f"转录错误：{e}", logging.WARNING)
                    print(f"[AudioCapture] 转录错误：{e}", flush=True)
                    import traceback
                    traceback.print_exc()
            
            print(f"[AudioCapture] 录音循环结束", flush=True)
            log_system("录音循环结束", logging.INFO)
                    
        except Exception as e:
            error_msg = f"音频捕获失败：{e}"
            log_system(error_msg, logging.ERROR)
            print(f"[AudioCapture] 错误：{e}")
            self.error_occurred.emit(error_msg)
    
    def _get_loopback_device(self, pyaudio_instance):
        """获取 WASAPI loopback 设备索引"""
        try:
            # 获取所有设备
            device_count = pyaudio_instance.get_device_count()
            
            # 查找非 HDMI 的 loopback 设备
            for i in range(device_count):
                try:
                    info = pyaudio_instance.get_device_info_by_index(i)
                    name = info['name'].lower()
                    
                    # 跳过 HDMI/DP 设备
                    if any(kw in name for kw in ['nvidia', 'hdmi', 'displayport', 'amd']):
                        continue
                    
                    # 查找有输入通道的设备（可能是 loopback 或立体声混音）
                    if info['maxInputChannels'] > 0:
                        # 优先选择 Realtek 相关设备
                        if 'realtek' in name or 'wave' in name or 'stereo' in name or 'mix' in name:
                            log_system(f"找到音频设备：{info['name']} (索引:{i})", logging.INFO)
                            return i
                except Exception:
                    pass
            
            # 如果没找到，使用默认 loopback
            loopback = pyaudio_instance.get_default_wasapi_loopback()
            log_system(f"使用默认 loopback: {loopback['name']} (索引:{loopback['index']})", logging.INFO)
            return loopback['index']
            
        except Exception as e:
            log_system(f"无法获取音频设备：{e}", logging.WARNING)
            return 0  # 默认设备
    
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
    
    def _on_realtime_update(self, text):
        """实时转录更新回调"""
        if text.strip():
            self.real_time_update.emit(text)
    
    def _on_recording_start(self):
        """录音开始回调"""
        self.recording_started.emit()
    
    def _on_recording_stop(self):
        """录音停止回调"""
        self.recording_stopped.emit()
    
    def stop(self):
        """停止音频捕获"""
        self._running = False
        
        if self.recorder:
            try:
                self.recorder.shutdown()
            except Exception:
                pass
        
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
    
    def is_running(self) -> bool:
        """是否正在运行"""
        return self._running


class SimulatedAudioCapture(QObject):
    """
    模拟音频捕获（用于测试，无需 VB-Cable）
    实际使用时请切换到 AudioCapture
    """
    
    transcription_ready = pyqtSignal(str)
    real_time_update = pyqtSignal(str)
    recording_started = pyqtSignal()
    recording_stopped = pyqtSignal()
    error_occurred = pyqtSignal(str)
    
    def __init__(self, config):
        super().__init__()
        self.config = config
        self._running = False
        self._test_mode = True
    
    def start(self):
        """启动模拟模式"""
        self._running = True
        self.recording_started.emit()
        self.error_occurred.emit(
            "模拟模式：请安装 VB-Cable 并配置后使用真实音频捕获\n"
            "详见 README.md 中的配置说明"
        )
    
    def stop(self):
        """停止"""
        self._running = False
        self.recording_stopped.emit()
    
    def is_running(self) -> bool:
        return self._running
    
    def set_test_mode(self, enabled: bool):
        """设置测试模式"""
        self._test_mode = enabled
