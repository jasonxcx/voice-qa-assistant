"""
配置管理模块
"""
import yaml
import os
from pathlib import Path
from typing import Any, Optional


class Config:
    """配置文件管理器"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化配置管理器
        
        Args:
            config_path: 配置文件路径，默认使用项目根目录下的 config.yaml
        """
        if config_path is None:
            # 获取项目根目录（core 的父目录）
            project_root = Path(__file__).parent.parent
            self.config_path = project_root / "config.yaml"
        else:
            self.config_path = Path(config_path)
        self.config = {}
        self.load()
    
    def load(self) -> dict:
        """加载配置文件"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"配置文件不存在：{self.config_path}")
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        return self.config
    
    def save(self):
        """保存配置文件"""
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.safe_dump(self.config, f, allow_unicode=True, default_flow_style=False)
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值
        
        Args:
            key: 配置键，支持点分隔，如 "llm.qwen.api_key"
            default: 默认值
            
        Returns:
            配置值
        """
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any):
        """
        设置配置值
        
        Args:
            key: 配置键，支持点分隔
            value: 配置值
        """
        keys = key.split('.')
        config = self.config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
        self.save()
    
    @property
    def llm_mode(self) -> str:
        """获取大模型模式"""
        return self.get("llm.mode", "qwen")
    
    @property
    def qwen_api_key(self) -> str:
        """获取通义千问 API Key"""
        return self.get("llm.qwen.api_key", "")
    
    @property
    def qwen_model(self) -> str:
        """获取通义千问模型"""
        return self.get("llm.qwen.model", "qwen-max")
    
    @property
    def ollama_url(self) -> str:
        """获取 Ollama 基础 URL"""
        return self.get("llm.ollama.base_url", "http://localhost:11434")
    
    @property
    def ollama_model(self) -> str:
        """获取 Ollama 模型"""
        return self.get("llm.ollama.model", "qwen2.5:7b")
    
    @property
    def audio_device_index(self) -> int:
        """获取音频输入设备索引"""
        return self.get("audio.input_device_index", 1)
    
    @property
    def use_microphone(self) -> bool:
        """是否使用麦克风"""
        return self.get("audio.use_microphone", False)
    
    @property
    def stt_model(self) -> str:
        """获取 STT 模型"""
        return self.get("stt.model", "medium")
    
    @property
    def stt_language(self) -> str:
        """获取 STT 语言"""
        return self.get("stt.language", "zh")
    
    @property
    def stt_compute_type(self) -> str:
        """获取 STT 计算类型"""
        return self.get("stt.local.compute_type", "float32")
    
    @property
    def stt_device(self) -> str:
        """获取 STT 计算设备"""
        return self.get("stt.local.device", "cpu")
    
    @property
    def overlay_height(self) -> int:
        """获取字幕窗口高度"""
        return self.get("ui.overlay_height", 140)
    
    @property
    def overlay_width_ratio(self) -> float:
        """获取字幕窗口宽度比例"""
        return self.get("ui.overlay_width_ratio", 0.85)
    
    @property
    def font_size(self) -> int:
        """获取字体大小"""
        return self.get("ui.font_size", 28)
    
    def validate(self) -> tuple[bool, str]:
        """
        验证配置有效性
        
        Returns:
            (是否有效，错误信息)
        """
        llm_mode = self.llm_mode
        
        if llm_mode == "qwen":
            if not self.qwen_api_key or self.qwen_api_key == "YOUR_DASHSCOPE_API_KEY":
                return False, "请配置通义千问 API Key"
        elif llm_mode == "ollama":
            # Ollama 本地运行，无需验证
            pass
        elif llm_mode == "lmstudio":
            # LM Studio 本地运行，无需验证
            pass
        else:
            return False, f"未知的大模型模式：{llm_mode}"
        
        return True, ""


# 全局配置实例
_config: Optional[Config] = None


def get_config() -> Config:
    """获取全局配置实例"""
    global _config
    if _config is None:
        _config = Config()
    return _config


def reload_config() -> Config:
    """重新加载配置"""
    global _config
    _config = Config()
    return _config
