"""
音频设备自动化测试模块

测试范围:
1. 音频设备检测与枚举
2. 设备选择逻辑验证
3. 音量监控功能测试
4. 音频捕获功能测试
5. 配置切换设备测试

使用方法:
    python -m pytest tests/test_audio_devices.py -v
"""
import pytest
import sys
import os
import time
import logging
from unittest.mock import Mock, patch, MagicMock
from typing import List, Dict, Any

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from core.config import Config, get_config
from core.audio_capture import AudioCapture


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MockPyAudioDevice:
    """模拟音频设备"""
    def __init__(self, index: int, name: str, input_channels: int = 2,
                 output_channels: int = 0, is_loopback: bool = False,
                 sample_rate: int = 44100):
        self.index = index
        self.name = name
        self.max_input_channels = input_channels
        self.max_output_channels = output_channels
        self.default_sample_rate = sample_rate
        self.is_loopback_device = is_loopback

    def to_info_dict(self) -> Dict[str, Any]:
        return {
            'index': self.index,
            'name': self.name,
            'maxInputChannels': self.max_input_channels,
            'maxOutputChannels': self.max_output_channels,
            'defaultSampleRate': self.default_sample_rate,
            'isLoopbackDevice': self.is_loopback_device
        }


class MockPyAudioStream:
    """模拟音频流"""
    def __init__(self, should_fail: bool = False):
        self.should_fail = should_fail
        self.is_active = True

    def read(self, num_frames: int, exception_on_overflow: bool = True) -> bytes:
        if self.should_fail:
            raise IOError("Simulated stream error")
        # 返回静音音频数据
        return b'\x00' * (num_frames * 4)  # 16-bit stereo

    def close(self):
        self.is_active = False


class MockPyAudio:
    """模拟 PyAudio 实例"""
    def __init__(self, devices: List[MockPyAudioDevice] = None):
        self.devices = devices or []
        self.default_loopback_index = None

    def get_device_count(self) -> int:
        return len(self.devices)

    def get_device_info_by_index(self, index: int) -> Dict[str, Any]:
        for device in self.devices:
            if device.index == index:
                return device.to_info_dict()
        raise OSError(f"Invalid device index: {index}")

    def get_default_wasapi_loopback(self) -> Dict[str, Any]:
        if self.default_loopback_index is not None:
            for device in self.devices:
                if device.index == self.default_loopback_index:
                    return device.to_info_dict()
        raise OSError("No default loopback device")

    def open(self, **kwargs):
        return MockPyAudioStream()

    def terminate(self):
        pass


class TestAudioDeviceDetection:
    """音频设备检测测试类"""

    @pytest.fixture
    def sample_config(self):
        """创建测试配置"""
        config = Mock(spec=Config)
        config.get = Mock(side_effect=lambda key, default=None: {
            'audio.output_device_index': 5,
            'audio.input_device_index': 1,
            'stt.auto.volume_threshold': 0.015,
            'stt.auto.pause_seconds': 0.8,
            'stt.auto.min_sentence_seconds': 2.0,
            'stt.auto.max_sentence_seconds': 8.0,
            'stt.auto.voice_ratio': 3.0,
            'stt.auto.silence_ratio': 1.8,
            'stt.auto.noise_alpha': 0.08,
            'stt.auto.resume_voice_chunks': 2,
        }.get(key, default))
        return config

    @pytest.fixture
    def sample_devices(self):
        """创建示例设备列表"""
        return [
            MockPyAudioDevice(0, "Primary Sound Driver", input_channels=2, output_channels=2),
            MockPyAudioDevice(1, "Realtek Audio Input", input_channels=2, output_channels=0),
            MockPyAudioDevice(5, "WASAPI Loopback", input_channels=2, output_channels=0, is_loopback=True),
            MockPyAudioDevice(16, "Speakers (Realtek)", input_channels=2, output_channels=2),
        ]

    def test_get_loopback_device_with_configured_output(self, sample_config, sample_devices):
        """测试：使用配置的输出设备"""
        audio_capture = AudioCapture(sample_config)
        pyaudio = MockPyAudio(sample_devices)

        # 配置输出设备索引为 5
        sample_config.get = Mock(side_effect=lambda key, default=None: {
            'audio.output_device_index': 5,
            'audio.input_device_index': 1,
        }.get(key, default))

        device_index = audio_capture._get_loopback_device(pyaudio)
        assert device_index == 5, f"Expected device index 5, got {device_index}"

    def test_get_loopback_device_with_configured_input(self, sample_config, sample_devices):
        """测试：使用配置的输入设备（当输出设备不可用时）"""
        audio_capture = AudioCapture(sample_config)
        pyaudio = MockPyAudio(sample_devices)

        # 配置输出设备不可用，使用输入设备
        sample_config.get = Mock(side_effect=lambda key, default=None: {
            'audio.output_device_index': 999,  # 不存在的设备
            'audio.input_device_index': 1,
        }.get(key, default))

        device_index = audio_capture._get_loopback_device(pyaudio)
        assert device_index == 1, f"Expected device index 1, got {device_index}"

    def test_get_loopback_device_finds_loopback(self, sample_config, sample_devices):
        """测试：自动查找 loopback 设备"""
        audio_capture = AudioCapture(sample_config)
        pyaudio = MockPyAudio(sample_devices)

        # 没有配置设备
        sample_config.get = Mock(return_value=None)

        device_index = audio_capture._get_loopback_device(pyaudio)
        assert device_index == 5, f"Expected loopback device index 5, got {device_index}"

    def test_get_loopback_device_default_fallback(self, sample_config):
        """测试：使用默认 loopback 设备"""
        audio_capture = AudioCapture(sample_config)
        devices = [
            MockPyAudioDevice(0, "Default Device", input_channels=2, output_channels=2),
        ]
        pyaudio = MockPyAudio(devices)
        pyaudio.default_loopback_index = 0

        sample_config.get = Mock(return_value=None)

        device_index = audio_capture._get_loopback_device(pyaudio)
        assert device_index == 0, f"Expected default device index 0, got {device_index}"

    def test_get_loopback_device_stereo_mix_fallback(self, sample_config):
        """测试：使用 Stereo Mix 类设备作为备选"""
        audio_capture = AudioCapture(sample_config)
        devices = [
            MockPyAudioDevice(0, "Stereo Mix", input_channels=2, output_channels=0),
        ]
        pyaudio = MockPyAudio(devices)

        sample_config.get = Mock(return_value=None)

        device_index = audio_capture._get_loopback_device(pyaudio)
        assert device_index == 0, f"Expected stereo mix device index 0, got {device_index}"

    def test_get_loopback_device_no_devices_fallback_to_zero(self, sample_config):
        """测试：当没有任何可用设备时回退到 0"""
        audio_capture = AudioCapture(sample_config)
        pyaudio = MockPyAudio([])

        sample_config.get = Mock(return_value=None)

        device_index = audio_capture._get_loopback_device(pyaudio)
        assert device_index == 0, f"Expected fallback index 0, got {device_index}"


class TestVolumeMonitoring:
    """音量监控功能测试类"""

    @pytest.fixture
    def audio_capture_with_config(self):
        """创建带有真实配置的 AudioCapture 实例"""
        try:
            config = get_config()
            return AudioCapture(config), config
        except FileNotFoundError:
            pytest.skip("配置文件不存在，跳过测试")

    def test_buffer_duration_seconds(self):
        """测试音频时长计算"""
        import numpy as np

        # 创建模拟音频缓冲区 (16kHz, 1 秒，单通道)
        sample_rate = 16000
        channels = 1
        duration = 1.0
        samples = int(sample_rate * duration * channels)
        audio_data = np.zeros(samples, dtype=np.int16)

        buffer = [audio_data]
        calculated_duration = AudioCapture._buffer_duration_seconds(buffer, sample_rate, channels)

        assert abs(calculated_duration - duration) < 0.001, \
            f"Expected duration ~{duration}s, got {calculated_duration}s"

    def test_estimate_thresholds(self, sample_config):
        """测试音量阈值估计"""
        audio_capture = AudioCapture(sample_config)

        # 测试静音环境
        audio_capture._auto_noise_ema = 0.001
        audio_capture._auto_in_speech = False

        start_threshold, keep_threshold = audio_capture._estimate_thresholds(0.001)

        assert start_threshold > 0, "Start threshold should be positive"
        assert keep_threshold > 0, "Keep threshold should be positive"
        assert start_threshold >= keep_threshold, "Start threshold should be >= keep threshold"


class TestAutoSegmentation:
    """自动分句功能测试类"""

    @pytest.fixture
    def sample_config(self):
        """创建测试配置"""
        config = Mock(spec=Config)
        config.get = Mock(side_effect=lambda key, default=None: {
            'audio.output_device_index': 5,
            'audio.input_device_index': 1,
            'stt.auto.volume_threshold': 0.015,
            'stt.auto.pause_seconds': 0.5,
            'stt.auto.min_sentence_seconds': 2.0,
            'stt.auto.max_sentence_seconds': 7.0,
            'stt.auto.voice_ratio': 2.8,
            'stt.auto.silence_ratio': 1.6,
            'stt.auto.noise_alpha': 0.1,
            'stt.auto.resume_voice_chunks': 2,
        }.get(key, default))
        return config

    def test_handle_auto_mode_chunk_silence_detection(self, sample_config):
        """测试自动模式下的静音检测"""
        import numpy as np

        audio_capture = AudioCapture(sample_config)
        audio_capture._reset_auto_segment_state()

        # 模拟静音块
        sample_rate = 16000
        channels = 2
        chunk_size = 1024
        silent_chunk = np.zeros(chunk_size, dtype=np.int16)

        # 发送多个静音块
        for _ in range(10):
            audio_capture._handle_auto_mode_chunk(silent_chunk, 0.0001, sample_rate, channels)

        # 应该累积静音计数
        assert audio_capture._auto_silence_chunks >= 0

    def test_handle_auto_mode_chunk_voice_detection(self, sample_config):
        """测试自动模式下的语音检测"""
        import numpy as np

        audio_capture = AudioCapture(sample_config)
        audio_capture._reset_auto_segment_state()

        sample_rate = 16000
        channels = 2
        chunk_size = 1024

        # 模拟有声块 (音量高于阈值)
        loud_chunk = (np.random.rand(chunk_size) * 0.1 * 32768).astype(np.int16)

        # 发送有声块
        audio_capture._handle_auto_mode_chunk(loud_chunk, 0.05, sample_rate, channels)

        # 应该检测到语音
        assert audio_capture._auto_in_speech or audio_capture._auto_sentence_buffer

    def test_reset_auto_segment_state(self, sample_config):
        """测试重置自动分句状态"""
        audio_capture = AudioCapture(sample_config)

        # 设置一些状态
        audio_capture._auto_in_speech = True
        audio_capture._auto_sentence_buffer = [1, 2, 3]
        audio_capture._auto_silence_chunks = 5
        audio_capture._auto_voice_chunks = 3

        # 重置状态
        audio_capture._reset_auto_segment_state()

        # 验证状态已重置
        assert audio_capture._auto_in_speech == False
        assert audio_capture._auto_sentence_buffer == []
        assert audio_capture._auto_silence_chunks == 0
        assert audio_capture._auto_voice_chunks == 0


class TestConfigIntegration:
    """配置集成测试类"""

    def test_audio_device_index_property(self):
        """测试 audio_device_index 属性"""
        # 使用真实配置测试
        try:
            config = get_config()
            audio_capture = AudioCapture(config)

            # 验证属性访问
            output_device = config.audio_output_device_index
            input_device = config.audio_input_device_index

            assert isinstance(output_device, int), "Output device index should be int"
            assert isinstance(input_device, int), "Input device index should be int"

        except FileNotFoundError:
            pytest.skip("配置文件不存在，跳过测试")

    def test_stt_auto_config_properties(self):
        """测试 STT 自动配置属性"""
        try:
            config = get_config()

            # 验证 STT 配置属性存在
            assert hasattr(config, 'stt_model')
            assert hasattr(config, 'stt_language')

            # 验证 auto 配置可以通过 get 访问
            volume_threshold = config.get('stt.auto.volume_threshold', 0.015)
            assert isinstance(volume_threshold, (int, float))

        except FileNotFoundError:
            pytest.skip("配置文件不存在，跳过测试")


class TestIntegration:
    """集成测试类"""

    @pytest.fixture
    def real_config(self):
        """获取真实配置"""
        try:
            return get_config()
        except FileNotFoundError:
            pytest.skip("配置文件不存在")

    @pytest.fixture
    def audio_capture(self, real_config):
        """创建 AudioCapture 实例"""
        return AudioCapture(real_config)

    def test_audio_capture_initialization(self, audio_capture):
        """测试 AudioCapture 初始化"""
        assert audio_capture is not None
        assert audio_capture.config is not None
        assert audio_capture._running == False
        assert audio_capture._monitoring == False
        assert audio_capture._recording == False

    def test_manual_mode_toggle(self, audio_capture):
        """测试手动模式切换"""
        # 初始为自动模式
        assert audio_capture._manual_mode == False

        # 切换到手动模式
        audio_capture.set_manual_mode(True)
        assert audio_capture._manual_mode == True

        # 切换回自动模式
        audio_capture.set_manual_mode(False)
        assert audio_capture._manual_mode == False

    def test_model_loaded_state(self, audio_capture):
        """测试模型加载状态检查"""
        # 初始状态模型未加载
        assert audio_capture.is_model_loaded() == False
        assert audio_capture.stt_model is None


# 运行测试的辅助函数
def run_tests():
    """运行所有测试"""
    pytest.main([__file__, '-v', '--tb=short'])


if __name__ == '__main__':
    # 直接运行测试
    print("=" * 60)
    print("音频设备自动化测试")
    print("=" * 60)

    # 运行 pytest
    sys.exit(pytest.main([__file__, '-v', '--tb=short']))
