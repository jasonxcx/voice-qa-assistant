"""
测试运行器 - 音频设备功能测试

此脚本提供统一的测试入口，支持多种运行模式。

使用方法:
    # 运行所有测试
    python tests/run_audio_tests.py

    # 只运行单元测试
    python tests/run_audio_tests.py --unit

    # 只运行端到端测试
    python tests/run_audio_tests.py --e2e

    # 生成覆盖率报告
    python tests/run_audio_tests.py --coverage

    # 详细输出
    python tests/run_audio_tests.py --verbose
"""
import sys
import os
import argparse
from datetime import datetime

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


def print_banner():
    """打印标题"""
    print("=" * 70)
    print("音频设备功能自动化测试套件")
    print("=" * 70)
    print(f"运行时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"项目目录：{project_root}")
    print("=" * 70)
    print()


def run_pytest(args: list) -> bool:
    """运行 pytest"""
    try:
        import pytest
        return pytest.main(args) == 0
    except ImportError:
        print("错误：pytest 未安装，请先安装：pip install pytest")
        return False


def run_unit_tests(verbose: bool = False):
    """运行单元测试"""
    print("\n" + "=" * 70)
    print("运行单元测试")
    print("=" * 70)

    args = [
        'tests/test_audio_device_functionality.py',
        '-p', 'no:warnings',
    ]

    if verbose:
        args.append('-v')

    return run_pytest(args)


def run_e2e_tests():
    """运行端到端测试"""
    print("\n" + "=" * 70)
    print("运行端到端测试")
    print("=" * 70)

    # E2E 测试作为脚本运行
    e2e_script = os.path.join(project_root, 'tests', 'test_audio_device_e2e.py')
    os.system(f'python "{e2e_script}"')
    return True


def run_all_tests(verbose: bool = False, coverage: bool = False):
    """运行所有测试"""
    print("\n" + "=" * 70)
    print("运行所有测试")
    print("=" * 70)

    args = [
        'tests/test_audio_device_functionality.py',
        'tests/test_audio_device_e2e.py',
        '-p', 'no:warnings',
    ]

    if verbose:
        args.append('-v')

    if coverage:
        try:
            import coverage
            args = [
                'tests/',
                '--cov=core/audio_capture',
                '--cov=core/config',
                '--cov-report=term-missing',
                '-p', 'no:warnings',
            ]
            if verbose:
                args.append('-v')
        except ImportError:
            print("警告：coverage 未安装，跳过覆盖率报告")

    return run_pytest(args)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='音频设备功能测试运行器'
    )
    parser.add_argument(
        '--unit',
        action='store_true',
        help='只运行单元测试'
    )
    parser.add_argument(
        '--e2e',
        action='store_true',
        help='只运行端到端测试'
    )
    parser.add_argument(
        '--coverage',
        action='store_true',
        help='生成覆盖率报告'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='详细输出'
    )
    parser.add_argument(
        '--list',
        action='store_true',
        help='列出所有测试'
    )

    args = parser.parse_args()

    print_banner()

    # 列出测试
    if args.list:
        print("可用测试:")
        print("  - tests/test_audio_device_functionality.py")
        print("    设备检测、设备选择、设备切换、Loopback 支持、")
        print("    音量监控、自动分句、转录模式、配置集成")
        print()
        print("  - tests/test_audio_device_e2e.py")
        print("    端到端场景测试：视频会议、本地扬声器、麦克风")
        print()
        sys.exit(0)

    # 运行测试
    success = True

    if args.unit:
        success = run_unit_tests(args.verbose)
    elif args.e2e:
        success = run_e2e_tests()
    else:
        success = run_all_tests(args.verbose, args.coverage)

    print()
    print("=" * 70)
    if success:
        print("测试完成：所有测试通过")
    else:
        print("测试完成：部分测试失败")
    print("=" * 70)

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
