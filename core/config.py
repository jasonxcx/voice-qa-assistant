"""
配置管理模块

配置结构说明:
- llm.api_key, llm.base_url, llm.model: 临时配置（运行时使用，切换模式时从 provider 复制）
- llm.mode: 当前使用的模式
- llm.provider.xxx: 永久配置（保存各 provider 的默认配置）
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
            key: 配置键，支持点分隔，如 "llm.provider.openai.api_key"
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

    def switch_llm_from_file(self, name: str):
        """
        根据配置文件切换 LLM - 将 provider 中的配置复制到临时配置

        Args:
            name: provider 名称，如 "openai", "ollama", "lmstudio"
        """
        provider = self.get(f"llm.provider.{name}", {})
        if not provider:
            provider = {}

        # 设置临时配置为 provider 中的值
        self.set("llm.mode", name)
        
        # 只在 provider 有对应配置时才覆盖，否则保留现有值
        if "api_key" in provider:
            self.set("llm.api_key", provider.get("api_key", ""))
        if "base_url" in provider:
            self.set("llm.base_url", provider.get("base_url", ""))
        if "model" in provider:
            self.set("llm.model", provider.get("model", ""))

    def get_provider_config(self, name: str) -> dict:
        """获取指定 provider 的配置"""
        return self.get(f"llm.provider.{name}", {})

    def update_provider_config(self, name: str, key: str, value: Any):
        """
        更新指定 provider 的配置

        Args:
            name: provider 名称
            key: 配置键，如 "api_key", "base_url", "model"
            value: 配置值
        """
        provider_key = f"llm.provider.{name}.{key}"
        self.set(provider_key, value)

    def validate(self) -> tuple[bool, str]:
        """
        验证配置有效性

        Returns:
            (是否有效，错误信息)
        """
        if not self.llm_base_url.startswith("http://127.0.0.1") and not self.llm_api_key:
            return False, f"请配置 {self.llm_mode} 的 API Key"
        return True, ""

    @property
    def llm_mode(self) -> str:
        """获取当前 LLM 模式"""
        return self.get("llm.mode", "openai")

    @property
    def llm_model(self) -> str:
        """获取当前使用的 LLM 模型"""
        return self.get("llm.model", "qwen3.5-plus")

    @property
    def llm_base_url(self) -> str:
        """获取当前使用的 LLM API 基础 URL"""
        default_url = "http://127.0.0.1:1234" if self.llm_mode == "lmstudio" else "https://coding.dashscope.aliyuncs.com/v1"
        return self.get("llm.base_url", default_url)

    @property
    def llm_api_key(self) -> str:
        """获取当前使用的 LLM API Key"""
        return self.get("llm.api_key", "")

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

    @property
    def icon_path(self) -> str:
        """获取图标路径"""
        return self.get("ui.icon", "")

    @property
    def overlay_border_radius(self) -> int:
        """获取字幕窗口边框圆角大小"""
        return self.get("ui.overlay_border_radius", 12)

    def _read_prompt_file(self, relative_path: str, default: str = "") -> str:
        """从文件读取提示词内容，如果文件不存在或读取失败则返回默认值"""
        if not relative_path:
            return default
        project_root = Path(__file__).parent.parent
        file_path = project_root / relative_path
        try:
            if file_path.exists():
                return file_path.read_text(encoding='utf-8').strip()
        except Exception:
            pass
        return default

    @property
    def stt_initial_prompt(self) -> str:
        """获取 STT 转录提示词"""
        return self.get("stt.initial_prompt", "面试场景，包含技术术语如 Java, Python, MySQL, Redis, Kafka, Docker, Kubernetes, 微服务，分布式系统，算法，数据结构等。")

    @property
    def stt_hotwords(self) -> str:
        """获取 STT 热词"""
        return self.get("stt.hotwords", "Java Python MySQL Redis Kafka Docker Kubernetes Spring TensorFlow PyTorch 微服务 分布式 算法 数据结构 多线程 并发 API SDK HTTP TCP IP")

    @property
    def llm_system_prompt_base(self) -> str:
        """获取 LLM 基础系统提示词（从文件读取）"""
        prompt_file = self.get("llm.prompts.base", "")
        return self._read_prompt_file(prompt_file, "你是一个熟悉计算机专业知识的Java工程师助手。")

    @property
    def llm_temperature(self) -> float:
        """获取 LLM 温度参数"""
        return self.get("llm.generation.temperature", 0.3)

    @property
    def llm_max_completion_tokens(self) -> int:
        """获取 LLM 最大生成 token 数"""
        return self.get("llm.generation.max_completion_tokens", 500)

    @property
    def llm_max_completion_tokens_stream(self) -> int:
        """获取 LLM 流式最大生成 token 数"""
        return self.get("llm.generation.max_completion_tokens_stream", 1000)

    @property
    def llm_reasoning_effort(self) -> str:
        """获取 LLM 思考强度"""
        return self.get("llm.generation.reasoning_effort", "none")


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
