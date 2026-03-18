"""
日志模块 - 记录 STT 转录和大模型回答
"""
import os
import logging
from datetime import datetime
from colorama import init, Fore, Style

# 初始化 colorama（Windows 支持）
init()


class ColoredFormatter(logging.Formatter):
    """彩色日志格式化器"""
    
    grey = "\x1b[38;21m"
    yellow = "\x1b[33;21m"
    red = "\x1b[31;21m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    
    format_str = "%(asctime)s - %(levelname)s - %(message)s"
    
    FORMATS = {
        logging.DEBUG: grey + format_str + Style.RESET_ALL,
        logging.INFO: Fore.GREEN + format_str + Style.RESET_ALL,
        logging.WARNING: Fore.YELLOW + format_str + Style.RESET_ALL,
        logging.ERROR: Fore.RED + format_str + Style.RESET_ALL,
        logging.CRITICAL: Fore.RED + Style.BRIGHT + format_str + Style.RESET_ALL,
    }
    
    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno, self.format_str)
        formatter = logging.Formatter(log_fmt, datefmt='%Y-%m-%d %H:%M:%S')
        return formatter.format(record)


def setup_logger(name: str, log_file: str = None, level: int = logging.INFO) -> logging.Logger:
    """
    设置日志记录器
    
    Args:
        name: 日志记录器名称
        log_file: 日志文件路径（可选）
        level: 日志级别
        
    Returns:
        Logger 对象
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # 避免重复添加 handler
    if logger.handlers:
        return logger
    
    # 控制台 handler（彩色）
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(ColoredFormatter())
    logger.addHandler(console_handler)
    
    # 文件 handler（如果有指定文件）
    if log_file:
        # 确保日志目录存在
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(level)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    return logger


# 创建专用日志记录器
stt_logger = setup_logger(
    'STT',
    log_file='logs/stt.log',
    level=logging.INFO
)

llm_logger = setup_logger(
    'LLM',
    log_file='logs/llm.log',
    level=logging.INFO
)

system_logger = setup_logger(
    'System',
    log_file='logs/system.log',
    level=logging.INFO
)


def log_stt(text: str, source: str = "transcription"):
    """
    记录 STT 转录文本
    
    Args:
        text: 转论文本
        source: 来源（transcription/realtime）
    """
    stt_logger.info(f"[{source}] {text}")


def log_llm(question: str, answer: str, model: str = "unknown"):
    """
    记录 LLM 问答
    
    Args:
        question: 问题
        answer: 回答
        model: 模型名称
    """
    llm_logger.info(f"[{model}] Q: {question} | A: {answer}")


def log_system(message: str, level: int = logging.INFO):
    """
    记录系统日志
    
    Args:
        message: 日志内容
        level: 日志级别
    """
    system_logger.log(level, message)
