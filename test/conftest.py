"""
pytest 配置 - 音频设备测试
"""
import pytest
import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


def pytest_configure(config):
    """配置 pytest"""
    # 设置日志级别
    config.option.log_cli = True
    config.option.log_cli_level = "INFO"


@pytest.fixture(scope="session")
def project_root_path():
    """返回项目根目录路径"""
    return project_root


@pytest.fixture(scope="session")
def test_data_dir():
    """返回测试数据目录"""
    return os.path.join(project_root, 'tests', 'data')


# 自定义标记
def pytest_configure(config):
    config.addinivalue_line(
        "markers", "device_test: 标记为音频设备测试"
    )
    config.addinivalue_line(
        "markers", "integration: 标记为集成测试"
    )
    config.addinivalue_line(
        "markers", "e2e: 标记为端到端测试"
    )
    config.addinivalue_line(
        "markers", "slow: 标记为慢速测试"
    )
