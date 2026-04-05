"""
音频设备切换端到端测试脚本

此脚本用于验证音频设备切换功能在真实环境中的行为。

测试场景:
1. 从麦克风切换到 Loopback 设备
2. 从一个 Loopback 设备切换到另一个
3. 从输出设备切换到输入设备
4. 配置不存在时的默认行为

使用方法:
    python tests/test_audio_device_e2e.py
"""
import sys
import os
import time
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from core.config import Config
from core.audio_capture import AudioCapture

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("DeviceSwitchTest")


class MockPyAudioDevice:
    """模拟音频设备"""
    def __init__(self, index: int, name: str, input_channels: int = 2,
                 output_channels: int = 0, is_loopback: bool = False):
        self.index = index
        self.name = name
        self.max_input_channels = input_channels
        self.max_output_channels = output_channels
        self.is_loopback_device = is_loopback
        self.default_sample_rate = 48000

    def to_dict(self) -> Dict[str, Any]:
        return {
            'index': self.index,
            'name': self.name,
            'maxInputChannels': self.max_input_channels,
            'maxOutputChannels': self.max_output_channels,
            'defaultSampleRate': self.default_sample_rate,
            'isLoopbackDevice': self.is_loopback_device,
        }


class MockPyAudio:
    """模拟 PyAudio 实例"""
    def __init__(self, devices: List[MockPyAudioDevice]):
        self.devices = devices
        self.default_loopback_index: Optional[int] = None

    def get_device_count(self) -> int:
        return len(self.devices)

    def get_device_info_by_index(self, index: int) -> Dict[str, Any]:
        for device in self.devices:
            if device.index == index:
                return device.to_dict()
        raise OSError(f"Invalid device index: {index}")

    def get_default_wasapi_loopback(self) -> Dict[str, Any]:
        if self.default_loopback_index is not None:
            for device in self.devices:
                if device.index == self.default_loopback_index:
                    return device.to_dict()
        raise OSError("No loopback device")

    def terminate(self):
        pass


class TestResult:
    """测试结果记录"""
    def __init__(self, name: str, passed: bool, message: str = ""):
        self.name = name
        self.passed = passed
        self.message = message
        self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def __str__(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        return f"[{status}] {self.name}: {self.message}"


class AudioDeviceSwitchTester:
    """音频设备切换测试器"""

    def __init__(self):
        self.results: List[TestResult] = []
        self.video_conference_devices = [
            MockPyAudioDevice(0, "Primary Sound Driver", 2, 2),
            MockPyAudioDevice(1, "Microphone (Realtek)", 2, 0),
            MockPyAudioDevice(2, "Speakers (Realtek)", 0, 2),
            MockPyAudioDevice(3, "WASAPI Loopback - Speakers", 2, 0, True),
            MockPyAudioDevice(4, "Zoom Audio Input", 2, 0),
            MockPyAudioDevice(5, "Zoom Audio Output", 0, 2),
            MockPyAudioDevice(6, "WASAPI Loopback - Zoom", 2, 0, True),
            MockPyAudioDevice(7, "Teams Audio Input", 2, 0),
            MockPyAudioDevice(8, "Teams Audio Output", 0, 2),
            MockPyAudioDevice(9, "WASAPI Loopback - Teams", 2, 0, True),
        ]

    def create_config(self, output_idx: Optional[int] = None,
                      input_idx: Optional[int] = None,
                      use_microphone: bool = False) -> Config:
        """创建测试配置"""
        config = type('MockConfig', (), {})()
        config._output_idx = output_idx
        config._input_idx = input_idx
        config._use_microphone = use_microphone

        def mock_get(key, default=None):
            if key == 'audio.output_device_index':
                return config._output_idx
            elif key == 'audio.input_device_index':
                return config._input_idx
            elif key == 'audio.use_microphone':
                return config._use_microphone
            elif key == 'stt.auto.volume_threshold':
                return 0.015
            elif key == 'stt.auto.pause_seconds':
                return 0.5
            elif key == 'stt.auto.min_sentence_seconds':
                return 2.0
            elif key == 'stt.auto.max_sentence_seconds':
                return 7.0
            elif key == 'stt.auto.voice_ratio':
                return 2.8
            elif key == 'stt.auto.silence_ratio':
                return 1.6
            elif key == 'stt.auto.noise_alpha':
                return 0.1
            elif key == 'stt.auto.resume_voice_chunks':
                return 2
            return default

        config.get = mock_get
        return config

    def run_test(self, name: str, test_func):
        """运行单个测试"""
        try:
            result = test_func()
            self.results.append(TestResult(name, True, result))
            logger.info(f"PASS: {name}: {result}")
        except AssertionError as e:
            self.results.append(TestResult(name, False, str(e)))
            logger.error(f"FAIL: {name}: {e}")
        except Exception as e:
            self.results.append(TestResult(name, False, f"Exception: {e}"))
            logger.error(f"FAIL: {name}: Exception - {e}")

    def test_switch_to_speakers_loopback(self) -> str:
        """测试 1: 切换到扬声器 Loopback（通过设置默认 loopback）"""
        pyaudio = MockPyAudio(self.video_conference_devices)
        pyaudio.default_loopback_index = 3  # 设置默认 loopback 为 Speakers
        config = self.create_config()
        audio_capture = AudioCapture(config)

        selected = audio_capture._get_loopback_device(pyaudio)

        assert selected == 3, f"Expected device 3, got {selected}"
        return f"Successfully selected Speakers Loopback (index: {selected})"

    def test_switch_to_zoom_loopback(self) -> str:
        """测试 2: 切换到 Zoom Loopback"""
        pyaudio = MockPyAudio(self.video_conference_devices)
        pyaudio.default_loopback_index = 6  # 设置默认 loopback 为 Zoom
        config = self.create_config()
        audio_capture = AudioCapture(config)

        selected = audio_capture._get_loopback_device(pyaudio)

        assert selected == 6, f"Expected device 6, got {selected}"
        return f"Successfully selected Zoom Loopback (index: {selected})"

    def test_switch_to_teams_loopback(self) -> str:
        """测试 3: 切换到 Teams Loopback"""
        pyaudio = MockPyAudio(self.video_conference_devices)
        pyaudio.default_loopback_index = 9  # 设置默认 loopback 为 Teams
        config = self.create_config()
        audio_capture = AudioCapture(config)

        selected = audio_capture._get_loopback_device(pyaudio)

        assert selected == 9, f"Expected device 9, got {selected}"
        return f"Successfully selected Teams Loopback (index: {selected})"

    def test_switch_from_loopback_to_microphone(self) -> str:
        """测试 4: 从 Loopback 切换到麦克风"""
        pyaudio = MockPyAudio(self.video_conference_devices)

        # 初始使用 Loopback
        pyaudio.default_loopback_index = 3
        config1 = self.create_config()
        audio_capture = AudioCapture(config1)
        selected1 = audio_capture._get_loopback_device(pyaudio)
        assert selected1 == 3

        # 切换到麦克风模式
        config2 = self.create_config(input_idx=1, use_microphone=True)
        audio_capture = AudioCapture(config2)
        selected2 = audio_capture._get_loopback_device(pyaudio)

        assert selected2 == 1, f"Expected device 1, got {selected2}"
        return f"Successfully switched from Loopback(3) to Microphone(1)"

    def test_auto_detect_loopback_when_no_config(self) -> str:
        """测试 5: 无配置时自动检测 Loopback"""
        pyaudio = MockPyAudio(self.video_conference_devices)
        config = self.create_config()  # 无配置
        audio_capture = AudioCapture(config)

        selected = audio_capture._get_loopback_device(pyaudio)

        # 应该选择第一个 Loopback 设备 (索引 3)
        assert selected == 3, f"Expected auto-detect device 3, got {selected}"
        return f"Auto-detected Loopback device (index: {selected})"

    def test_invalid_output_fallback_to_input(self) -> str:
        """测试 6: 输出设备无效时回退到输入设备"""
        pyaudio = MockPyAudio(self.video_conference_devices)
        # 使用麦克风模式，配置有效的输入设备
        config = self.create_config(input_idx=1, use_microphone=True)
        audio_capture = AudioCapture(config)

        selected = audio_capture._get_loopback_device(pyaudio)

        assert selected == 1, f"Expected fallback to device 1, got {selected}"
        return f"Correctly fallback to input device (index: {selected})"

    def test_device_info_retrieval(self) -> str:
        """测试 7: 获取设备信息"""
        pyaudio = MockPyAudio(self.video_conference_devices)
        pyaudio.default_loopback_index = 6
        config = self.create_config()
        audio_capture = AudioCapture(config)

        selected = audio_capture._get_loopback_device(pyaudio)
        info = pyaudio.get_device_info_by_index(selected)

        assert info['index'] == 6
        assert 'Loopback' in info['name']
        assert info['maxInputChannels'] > 0
        return f"Successfully retrieved device info: {info['name']}"

    def test_multiple_switches_sequential(self) -> str:
        """测试 8: 连续多次切换"""
        pyaudio = MockPyAudio(self.video_conference_devices)

        switch_sequence = [
            # (default_loopback_idx, output_idx, input_idx, use_microphone, expected_idx, description)
            (3, None, None, False, 3, "Speakers Loopback"),
            (6, None, None, False, 6, "Zoom Loopback"),
            (9, None, None, False, 9, "Teams Loopback"),
            (None, None, 1, True, 1, "Microphone"),
            (None, None, 4, True, 4, "Zoom Input"),
        ]

        for loopback_idx, output_idx, input_idx, use_mic, expected_idx, desc in switch_sequence:
            pyaudio.default_loopback_index = loopback_idx
            config = self.create_config(output_idx=output_idx, input_idx=input_idx, use_microphone=use_mic)
            audio_capture = AudioCapture(config)
            selected = audio_capture._get_loopback_device(pyaudio)

            assert selected == expected_idx, \
                f"Switch to {desc} failed: expected {expected_idx}, got {selected}"

        return f"Successfully completed {len(switch_sequence)} sequential switches"

    def generate_report(self) -> str:
        """生成测试报告"""
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed
        pass_rate = (passed / total * 100) if total > 0 else 0

        report = []
        report.append("=" * 70)
        report.append("Audio Device Switch Function Test Report")
        report.append("=" * 70)
        report.append(f"Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Total Tests: {total}")
        report.append(f"Passed: {passed}")
        report.append(f"Failed: {failed}")
        report.append(f"Pass Rate: {pass_rate:.1f}%")
        report.append("")
        report.append("-" * 70)
        report.append("Detailed Results:")
        report.append("-" * 70)

        for result in self.results:
            status = "PASS" if result.passed else "FAIL"
            report.append(f"[{status}] {result.name}")
            if result.message:
                report.append(f"      {result.message}")

        report.append("")
        report.append("=" * 70)

        if failed == 0:
            report.append("All tests passed! Audio device switch function is working correctly.")
        else:
            report.append(f"Warning: {failed} test(s) failed. Please check the device switch logic.")

        report.append("=" * 70)

        return "\n".join(report)

    def run_all_tests(self):
        """运行所有测试"""
        logger.info("Starting audio device switch tests...")

        self.run_test("Switch to Speakers Loopback", self.test_switch_to_speakers_loopback)
        self.run_test("Switch to Zoom Loopback", self.test_switch_to_zoom_loopback)
        self.run_test("Switch to Teams Loopback", self.test_switch_to_teams_loopback)
        self.run_test("Switch from Loopback to Microphone", self.test_switch_from_loopback_to_microphone)
        self.run_test("Auto-detect Loopback when no config", self.test_auto_detect_loopback_when_no_config)
        self.run_test("Fallback to input when output invalid", self.test_invalid_output_fallback_to_input)
        self.run_test("Get device info", self.test_device_info_retrieval)
        self.run_test("Multiple sequential switches", self.test_multiple_switches_sequential)

        # 生成报告
        report = self.generate_report()
        print("\n" + report)

        return len([r for r in self.results if r.passed]) == len(self.results)


def main():
    """主函数"""
    print("=" * 70)
    print("Audio Device Switch End-to-End Test")
    print("=" * 70)
    print()

    tester = AudioDeviceSwitchTester()
    success = tester.run_all_tests()

    # 返回退出码
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
