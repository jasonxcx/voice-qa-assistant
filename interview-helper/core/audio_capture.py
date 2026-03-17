"""
音频捕获模块 - 基于 RealtimeSTT
"""
import threading
from typing import Optional, Callable
from PyQt5.QtCore import pyqtSignal, QObject


class AudioCapture(QObject):
    """音频捕获和 STT 转换"""
    
    # Qt 信号
    transcription_ready = pyqtSignal(str)  # 转录文本就绪
    real_time_update = pyqtSignal(str)     # 实时转录更新
    recording_started = pyqtSignal()       # 开始录音
    recording_stopped = pyqtSignal()       # 停止录音
    error_occurred = pyqtSignal(str)       # 错误发生
    
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.recorder = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
    
    def start(self):
        """在独立线程中启动音频捕获"""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
    
    def _run(self):
        """运行 RealtimeSTT 录音循环"""
        try:
            from RealtimeSTT import AudioToTextRecorder
            
            # 配置 RealtimeSTT
            self.recorder = AudioToTextRecorder(
                model=self.config.stt_model,
                language=self.config.stt_language,
                device=self.config.stt_device,
                input_device_index=self.config.audio_device_index,
                use_microphone=self.config.use_microphone,
                enable_realtime_transcription=True,
                on_realtime_transcription_update=self._on_realtime_update,
                on_recording_start=self._on_recording_start,
                on_recording_stop=self._on_recording_stop,
                spinner=False,
                level=30,  # WARNING
            )
            
            # 主录音循环
            while self._running:
                def process_text(text):
                    """转录完成回调"""
                    if text.strip():
                        self.transcription_ready.emit(text)
                
                self.recorder.text(process_text)
                
        except Exception as e:
            self.error_occurred.emit(str(e))
    
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
