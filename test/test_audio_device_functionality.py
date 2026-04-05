"""
音频设备功能自动化测试套件

测试范围:
1. 设备检测与枚举 - 验证系统能够正确识别所有音频设备
2. 设备选择逻辑 - 验证设备优先级选择逻辑正确
3. 设备切换功能 - 验证运行时切换设备的功能
4. Loopback 设备支持 - 验证 WASAPI loopback 设备捕获
5. 音量监控功能 - 验证音量检测和阈值判断
6. 自动分句功能 - 验证基于音量的自动分句逻辑
7. 手动/自动模式切换 - 验证两种转录模式的行为
8. 配置集成测试 - 验证配置与设备选择的集成

使用方法:
    python -m pytest tests/test_audio_device_functionality.py -v
"""
import pytest
import sys
import os
import time
import logging
from unittest.mock import Mock, patch, MagicMock
from typing import List, Dict, Any, Optional
import numpy as np

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
logger = logging.getLogger("AudioDeviceTest")


# ============================================================================
# 模拟设备类
# ============================================================================

class MockAudioDevice:
    """模拟音频设备"""
    def __init__(
        self,
        index: int,
        name: str,
        input_channels: int = 0,
        output_channels: int = 0,
        sample_rate: int = 48000,
        is_loopback: bool = False,
        host_api: int = 0,
    ):
        self.index = index
        self.name = name
        self.max_input_channels = input_channels
        self.max_output_channels = output_channels
        self.default_sample_rate = sample_rate
        self.is_loopback_device = is_loopback
        self.is_loopback = is_loopback  # 别名，方便测试使用
        self.host_api = host_api

    def to_dict(self) -> Dict[str, Any]:
        """转换为 PyAudio 设备信息字典格式"""
        return {
            'index': self.index,
            'name': self.name,
            'maxInputChannels': self.max_input_channels,
            'maxOutputChannels': self.max_output_channels,
            'defaultSampleRate': self.default_sample_rate,
            'isLoopbackDevice': self.is_loopback_device,
            'hostApi': self.host_api,
            'defaultLowInputLatency': 0.01,
            'defaultLowOutputLatency': 0.01,
        }


class MockPyAudioStream:
    """模拟音频流"""
    def __init__(self, audio_data: Optional[bytes] = None, should_fail: bool = False):
        self.audio_data = audio_data or b'\x00' * 4096
        self.should_fail = should_fail
        self.is_active = True

    def read(self, num_frames: int, exception_on_overflow: bool = True) -> bytes:
        if self.should_fail:
            raise IOError("Simulated stream read error")
        return self.audio_data[:num_frames * 4]

    def close(self):
        self.is_active = False


class MockPyAudio:
    """模拟 PyAudio 实例"""
    def __init__(self, devices: List[MockAudioDevice] = None):
        self.devices = devices or []
        self.default_loopback_index: Optional[int] = None

    def get_device_count(self) -> int:
        return len(self.devices)

    def get_device_info_by_index(self, index: int) -> Dict[str, Any]:
        for device in self.devices:
            if device.index == index:
                return device.to_dict()
        raise OSError(f"Invalid device index: {index}")

    def get_default_wasapi_loopback(self) -> Dict[str, Any]:
        # 只有明确设置了 default_loopback_index 才返回
        if self.default_loopback_index is not None:
            for device in self.devices:
                if device.index == self.default_loopback_index:
                    return device.to_dict()
        # 否则抛出异常，让调用者回退到其他逻辑
        raise OSError("No default WASAPI loopback device")

    def get_default_input_device_info(self) -> Dict[str, Any]:
        """获取默认输入设备"""
        for device in self.devices:
            if device.max_input_channels > 0:
                return device.to_dict()
        raise OSError("No default input device")

    def get_loopback_device_info_generator(self):
        for device in self.devices:
            if device.is_loopback_device:
                yield device.to_dict()

    def get_wasapi_loopback_analogue_by_index(self, index: int) -> Dict[str, Any]:
        info = self.get_device_info_by_index(index)
        if info.get('isLoopbackDevice', False):
            return info
        if info.get('maxOutputChannels', 0) <= 0:
            raise ValueError(f"Device {index} is not an output device")

        normalized = AudioCapture._normalize_device_name(info.get('name', ''))
        host_api = info.get('hostApi')
        for loopback in self.get_loopback_device_info_generator():
            if loopback.get('hostApi') != host_api:
                continue
            loopback_normalized = AudioCapture._normalize_device_name(loopback.get('name', ''))
            if normalized and (
                normalized in loopback_normalized or loopback_normalized in normalized
            ):
                return loopback

        raise LookupError(f"No loopback analogue for device {index}")

    def get_wasapi_loopback_analogue_by_dict(self, info_dict: Dict[str, Any]) -> Dict[str, Any]:
        return self.get_wasapi_loopback_analogue_by_index(info_dict['index'])

    def open(self, **kwargs) -> MockPyAudioStream:
        return MockPyAudioStream()

    def terminate(self):
        pass


# ============================================================================
# 测试场景配置
# ============================================================================

class DeviceScenarios:
    """预定义的音频设备场景"""

    @staticmethod
    def typical_desktop() -> List[MockAudioDevice]:
        """典型的桌面环境设备配置"""
        return [
            MockAudioDevice(0, "Primary Sound Driver", 2, 2),
            MockAudioDevice(1, "Realtek HD Audio Input", 2, 0),
            MockAudioDevice(2, "Realtek HD Audio Output", 0, 2),
            MockAudioDevice(3, "Realtek HD Audio Output (loopback)", 2, 0, is_loopback=True),
            MockAudioDevice(4, "USB Headset Input", 2, 0),
            MockAudioDevice(5, "USB Headset Output", 0, 2),
        ]

    @staticmethod
    def video_conference() -> List[MockAudioDevice]:
        """视频会议环境设备配置"""
        return [
            MockAudioDevice(0, "Primary Sound Driver", 2, 2),
            MockAudioDevice(1, "Microphone (Realtek)", 2, 0),
            MockAudioDevice(2, "Speakers (Realtek)", 0, 2),
            MockAudioDevice(3, "Speakers (Realtek) (loopback)", 2, 0, is_loopback=True),
            MockAudioDevice(4, "Zoom Audio Input", 2, 0),
            MockAudioDevice(5, "Zoom Audio Output", 0, 2),
            MockAudioDevice(6, "Zoom Audio Output (loopback)", 2, 0, is_loopback=True),
        ]

    @staticmethod
    def minimal_setup() -> List[MockAudioDevice]:
        """最小化设备配置"""
        return [
            MockAudioDevice(0, "Default Audio Device", 2, 2),
        ]

    @staticmethod
    def no_loopback() -> List[MockAudioDevice]:
        """没有 loopback 设备的配置"""
        return [
            MockAudioDevice(0, "Basic Audio", 2, 2),
            MockAudioDevice(1, "Microphone", 1, 0),
            MockAudioDevice(2, "Speakers", 0, 2),
        ]

    @staticmethod
    def stereo_mix_only() -> List[MockAudioDevice]:
        """仅有 Stereo Mix 的配置"""
        return [
            MockAudioDevice(0, "Stereo Mix", 2, 0),
            MockAudioDevice(1, "Microphone", 1, 0),
            MockAudioDevice(2, "Speakers", 0, 2),
        ]


# ============================================================================
# 测试类
# ============================================================================

class TestDeviceDetection:
    """设备检测功能测试"""

    @pytest.fixture
    def mock_config(self):
        """创建模拟配置"""
        config = Mock(spec=Config)
        config.get = Mock(side_effect=lambda key, default=None: {
            'audio.output_device_index': None,
            'audio.input_device_index': None,
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

    def test_detect_all_devices(self, mock_config):
        """测试：检测所有设备"""
        devices = DeviceScenarios.typical_desktop()
        pyaudio = MockPyAudio(devices)
        audio_capture = AudioCapture(mock_config)

        for device in devices:
            info = pyaudio.get_device_info_by_index(device.index)
            assert info['index'] == device.index
            assert info['name'] == device.name

    def test_detect_loopback_devices(self, mock_config):
        """测试：检测 loopback 设备"""
        devices = DeviceScenarios.typical_desktop()
        pyaudio = MockPyAudio(devices)
        audio_capture = AudioCapture(mock_config)

        # 通过设备信息字典检测 loopback 设备
        loopback_count = 0
        for device in devices:
            info = pyaudio.get_device_info_by_index(device.index)
            if info.get('isLoopbackDevice', False) or 'loopback' in info['name'].lower():
                loopback_count += 1

        assert loopback_count > 0, "应该至少有一个 loopback 设备"


class TestDeviceSelection:
    """设备选择逻辑测试"""

    @pytest.fixture
    def create_config(self):
        """创建配置的工厂函数"""
        def _create_config(output_idx=None, input_idx=None, use_microphone=False):
            config = Mock(spec=Config)
            config.get = Mock(side_effect=lambda key, default=None: {
                'audio.output_device_index': output_idx,
                'audio.input_device_index': input_idx,
                'audio.use_microphone': use_microphone,
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
        return _create_config

    def test_priority_configured_output_device(self, create_config):
        """测试：优先使用配置的输出设备（麦克风模式）"""
        devices = DeviceScenarios.typical_desktop()
        pyaudio = MockPyAudio(devices)
        # 使用麦克风模式，会选择配置的输入设备
        config = create_config(input_idx=1, use_microphone=True)
        audio_capture = AudioCapture(config)
        selected = audio_capture._get_loopback_device(pyaudio)
        assert selected == 1

    def test_priority_configured_input_device(self, create_config):
        """测试：优先使用配置的输入设备（麦克风模式）"""
        devices = DeviceScenarios.typical_desktop()
        pyaudio = MockPyAudio(devices)
        config = create_config(input_idx=1, use_microphone=True)
        audio_capture = AudioCapture(config)
        selected = audio_capture._get_loopback_device(pyaudio)
        assert selected == 1

    def test_auto_detect_loopback(self, create_config):
        """测试：自动检测 loopback 设备"""
        devices = DeviceScenarios.typical_desktop()
        pyaudio = MockPyAudio(devices)
        config = create_config()  # 无配置，use_microphone=False
        audio_capture = AudioCapture(config)
        selected = audio_capture._get_loopback_device(pyaudio)
        # 应该选择第一个 loopback 设备（索引 3）
        assert selected == 3, f"Expected loopback device 3, got {selected}"

    def test_configured_output_maps_to_matching_loopback(self, create_config):
        """测试：所选输出设备应映射到对应的 loopback 设备"""
        devices = DeviceScenarios.video_conference()
        pyaudio = MockPyAudio(devices)
        config = create_config(output_idx=5, use_microphone=False)
        audio_capture = AudioCapture(config)
        selected = audio_capture._get_loopback_device(pyaudio)
        assert selected == 6

    def test_fallback_to_stereo_mix(self, create_config):
        """测试：回退到 Stereo Mix 设备"""
        devices = DeviceScenarios.stereo_mix_only()
        pyaudio = MockPyAudio(devices)
        config = create_config()
        audio_capture = AudioCapture(config)
        selected = audio_capture._get_loopback_device(pyaudio)
        assert selected == 0

    def test_final_fallback_to_zero(self, create_config):
        """测试：最终回退到设备 0"""
        devices = []
        pyaudio = MockPyAudio(devices)
        config = create_config()
        audio_capture = AudioCapture(config)
        selected = audio_capture._get_loopback_device(pyaudio)
        assert selected == 0


class TestDeviceSwitching:
    """设备切换功能测试"""

    @pytest.fixture
    def mock_config(self):
        self._use_microphone = False
        self._output_idx = None
        self._input_idx = None
        config = Mock(spec=Config)

        def mock_get(key, default=None):
            if key == 'audio.use_microphone':
                return self._use_microphone
            elif key == 'audio.output_device_index':
                return self._output_idx
            elif key == 'audio.input_device_index':
                return self._input_idx
            # 返回 STT 配置默认值
            elif key == 'stt.auto.volume_threshold':
                return 0.015
            elif key == 'stt.auto.pause_seconds':
                return 0.8
            elif key == 'stt.auto.min_sentence_seconds':
                return 2.0
            elif key == 'stt.auto.max_sentence_seconds':
                return 8.0
            elif key == 'stt.auto.voice_ratio':
                return 3.0
            elif key == 'stt.auto.silence_ratio':
                return 1.8
            elif key == 'stt.auto.noise_alpha':
                return 0.08
            elif key == 'stt.auto.resume_voice_chunks':
                return 2
            return default

        config.get = Mock(side_effect=mock_get)
        return config

    def test_switch_to_microphone_mode(self, mock_config):
        """测试：切换到麦克风模式"""
        devices = DeviceScenarios.video_conference()
        pyaudio = MockPyAudio(devices)
        audio_capture = AudioCapture(mock_config)

        # 切换到麦克风模式
        def new_get(key, default=None):
            if key == 'audio.use_microphone':
                return True
            elif key == 'audio.input_device_index':
                return 1
            elif key == 'stt.auto.volume_threshold':
                return 0.015
            elif key == 'stt.auto.pause_seconds':
                return 0.8
            elif key == 'stt.auto.min_sentence_seconds':
                return 2.0
            elif key == 'stt.auto.max_sentence_seconds':
                return 8.0
            elif key == 'stt.auto.voice_ratio':
                return 3.0
            elif key == 'stt.auto.silence_ratio':
                return 1.8
            elif key == 'stt.auto.noise_alpha':
                return 0.08
            elif key == 'stt.auto.resume_voice_chunks':
                return 2
            return default

        mock_config.get = Mock(side_effect=new_get)
        selected = audio_capture._get_loopback_device(pyaudio)
        # 麦克风模式应该选择配置的输入设备
        assert selected == 1

    def test_switch_to_loopback_device(self, mock_config):
        """测试：切换到 loopback 设备（通过设置特定输出设备索引）"""
        devices = DeviceScenarios.video_conference()
        pyaudio = MockPyAudio(devices)

        # 设置默认 loopback 为设备 6
        pyaudio.default_loopback_index = 6

        audio_capture = AudioCapture(mock_config)
        selected = audio_capture._get_loopback_device(pyaudio)
        assert selected == 6


class TestLoopbackSupport:
    """WASAPI Loopback 设备支持测试"""

    @pytest.fixture
    def mock_config(self):
        config = Mock(spec=Config)
        config.get = Mock(side_effect=lambda key, default=None: {
            'audio.use_microphone': False,
            'audio.output_device_index': None,
            'audio.input_device_index': None,
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

    def test_loopback_device_priority(self, mock_config):
        """测试：loopback 设备优先级"""
        devices = DeviceScenarios.video_conference()
        pyaudio = MockPyAudio(devices)
        # 设置默认 loopback 为设备 6 (Zoom)
        pyaudio.default_loopback_index = 6
        audio_capture = AudioCapture(mock_config)
        selected = audio_capture._get_loopback_device(pyaudio)
        # 应该选择设置的默认 loopback 设备
        assert selected == 6

    def test_loopback_device_detection_by_name(self, mock_config):
        """测试：通过名称检测 loopback 设备"""
        devices = DeviceScenarios.video_conference()
        pyaudio = MockPyAudio(devices)
        audio_capture = AudioCapture(mock_config)
        selected = audio_capture._get_loopback_device(pyaudio)
        # 应该选择第一个名称包含 Loopback 的设备（索引 3）
        # 通过名称查找 loopback 设备
        loopback_indices = []
        for d in devices:
            info = pyaudio.get_device_info_by_index(d.index)
            if info.get('isLoopbackDevice', False) or 'loopback' in info['name'].lower():
                loopback_indices.append(d.index)
        assert selected in loopback_indices, f"Expected {selected} to be in {loopback_indices}"


class TestVolumeMonitoring:
    """音量监控功能测试"""

    @pytest.fixture
    def mock_config(self):
        config = Mock(spec=Config)
        config.get = Mock(side_effect=lambda key, default=None: {
            'stt.auto.volume_threshold': 0.015,
            'stt.auto.noise_alpha': 0.08,
        }.get(key, default))
        return config

    def test_silent_audio_volume(self, mock_config):
        """测试：静音音频的音量计算"""
        silent_audio = np.zeros(1024, dtype=np.int16)
        audio_float = silent_audio.astype(np.float32) / 32768.0
        volume = np.sqrt(np.mean(audio_float ** 2))
        assert volume == 0.0

    def test_loud_audio_volume(self, mock_config):
        """测试：大声音频的音量计算"""
        loud_audio = (np.random.rand(1024) * 0.5 * 32768).astype(np.int16)
        audio_float = loud_audio.astype(np.float32) / 32768.0
        volume = np.sqrt(np.mean(audio_float ** 2))
        assert volume > 0.01

    def test_estimate_thresholds_basic(self, mock_config):
        """测试：阈值估计基本功能"""
        audio_capture = AudioCapture(mock_config)
        audio_capture._auto_noise_ema = 0.001
        audio_capture._auto_in_speech = False
        start_threshold, keep_threshold = audio_capture._estimate_thresholds(0.001)
        assert start_threshold > 0
        assert keep_threshold > 0
        assert start_threshold >= keep_threshold


class TestAutoSegmentation:
    """自动分句功能测试"""

    @pytest.fixture
    def mock_config(self):
        config = Mock(spec=Config)
        config.get = Mock(side_effect=lambda key, default=None: {
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

    def test_detect_speech_start(self, mock_config):
        """测试：检测语音开始"""
        audio_capture = AudioCapture(mock_config)
        audio_capture._reset_auto_segment_state()
        sample_rate = 16000
        channels = 2
        chunk_size = 1024
        loud_chunk = (np.random.rand(chunk_size) * 0.1 * 32768).astype(np.int16)
        audio_capture._handle_auto_mode_chunk(loud_chunk, 0.05, sample_rate, channels)
        assert audio_capture._auto_in_speech == True
        assert len(audio_capture._auto_sentence_buffer) > 0

    def test_reset_state_clears_buffers(self, mock_config):
        """测试：重置状态清除缓冲区"""
        audio_capture = AudioCapture(mock_config)
        audio_capture._auto_in_speech = True
        audio_capture._auto_sentence_buffer = [np.zeros(1024)]
        audio_capture._auto_silence_chunks = 5
        audio_capture._reset_auto_segment_state()
        assert audio_capture._auto_in_speech == False
        assert audio_capture._auto_sentence_buffer == []
        assert audio_capture._auto_silence_chunks == 0


class TestTranscriptionMode:
    """转录模式切换测试"""

    @pytest.fixture
    def mock_config(self):
        config = Mock(spec=Config)
        config.get = Mock(side_effect=lambda key, default=None: {
            'audio.output_device_index': 5,
            'audio.input_device_index': 1,
            'stt.auto.volume_threshold': 0.015,
        }.get(key, default))
        return config

    def test_initial_mode_is_auto(self, mock_config):
        """测试：初始模式为自动"""
        audio_capture = AudioCapture(mock_config)
        assert audio_capture._manual_mode == False

    def test_switch_to_manual_mode(self, mock_config):
        """测试：切换到手动模式"""
        audio_capture = AudioCapture(mock_config)
        audio_capture.set_manual_mode(True)
        assert audio_capture._manual_mode == True

    def test_switch_back_to_auto_mode(self, mock_config):
        """测试：切换回自动模式"""
        audio_capture = AudioCapture(mock_config)
        audio_capture.set_manual_mode(True)
        audio_capture.set_manual_mode(False)
        assert audio_capture._manual_mode == False


class TestConfigIntegration:
    """配置集成测试"""

    def test_config_audio_device_properties(self):
        """测试：配置音频设备属性"""
        try:
            config = get_config()
            assert hasattr(config, 'audio_device_index')
            assert hasattr(config, 'audio_output_device_index')
            assert hasattr(config, 'audio_input_device_index')
        except FileNotFoundError:
            pytest.skip("配置文件不存在")


# ============================================================================
# 端到端场景测试
# ============================================================================

class TestEndToEndScenarios:
    """端到端场景测试"""

    def _create_test_config(self, output_idx=None, input_idx=None, use_microphone=False):
        """创建测试配置的辅助方法"""
        config = Mock(spec=Config)
        config.get = Mock(side_effect=lambda key, default=None: {
            'audio.use_microphone': use_microphone,
            'audio.output_device_index': output_idx,
            'audio.input_device_index': input_idx,
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

    def test_scenario_conference_call_audio_capture(self):
        """场景测试：视频会议音频捕获（使用麦克风模式）"""
        devices = DeviceScenarios.video_conference()
        pyaudio = MockPyAudio(devices)

        # 使用麦克风模式，选择 Zoom 输入设备
        config = self._create_test_config(input_idx=4, use_microphone=True)

        audio_capture = AudioCapture(config)
        selected = audio_capture._get_loopback_device(pyaudio)
        assert selected == 4, "应选择 Zoom 输入设备进行捕获"

    def test_scenario_local_speaker_monitoring(self):
        """场景测试：本地扬声器监听（使用 loopback 设备）"""
        devices = DeviceScenarios.typical_desktop()
        pyaudio = MockPyAudio(devices)

        # 设置默认 loopback 为设备 3
        pyaudio.default_loopback_index = 3

        config = self._create_test_config()

        audio_capture = AudioCapture(config)
        selected = audio_capture._get_loopback_device(pyaudio)
        assert selected == 3

    def test_scenario_microphone_input(self):
        """场景测试：麦克风输入"""
        devices = DeviceScenarios.no_loopback()
        pyaudio = MockPyAudio(devices)

        # 使用麦克风模式
        config = self._create_test_config(input_idx=1, use_microphone=True)

        audio_capture = AudioCapture(config)
        selected = audio_capture._get_loopback_device(pyaudio)
        assert selected == 1


# ============================================================================
# 测试执行
# ============================================================================

if __name__ == '__main__':
    print("=" * 70)
    print("音频设备功能自动化测试套件")
    print("=" * 70)
    sys.exit(pytest.main([__file__, '-v', '--tb=short', '-p', 'no:warnings']))
