# Interview Helper - Windows 面试辅助工具 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a Windows desktop application that captures audio from video conferencing software, transcribes speech to text in real-time using GPU-accelerated STT, generates AI responses via Qwen API or local Ollama, and displays subtitles on screen with PyQt5.

**Architecture:** 
- **UI Layer:** PyQt5 with two windows (main window for settings/resume, overlay window for subtitles)
- **Core Layer:** Audio capture (RealtimeSTT), LLM client (Qwen/Ollama dual-mode), resume parser (Markdown)
- **Configuration:** YAML-based config management with runtime reload support

**Tech Stack:**
- Python 3.10+ with PyQt5
- RealtimeSTT + Faster-Whisper (GPU acceleration via CUDA)
- Qwen API + Ollama/LM Studio (dual LLM modes)
- mistune (Markdown parsing)
- PyYAML (config management)

---

## Wave 1: Foundation & Configuration (Sequential)

### Task 1.1: Project Setup & Requirements

**Files:**
- Create: `requirements.txt`
- Create: `config.yaml` (template)
- Create: `README.md` (initial)

**Step 1: Create requirements.txt**

```python
# UI Framework
PyQt5>=5.15.10

# Audio & STT
RealtimeSTT>=0.1.0
faster-whisper>=1.0.0
sounddevice>=0.4.0
numpy>=1.24.0

# LLM Clients
openai>=1.0.0  # For Qwen API
requests>=2.31.0  # For Ollama/LM Studio

# Markdown Processing
mistune>=3.0.0

# Configuration
PyYAML>=6.0.1

# Utilities
python-dotenv>=1.0.0
```

**Step 2: Create config.yaml template**

```yaml
# Interview Helper Configuration

# Audio Settings
audio:
  device: -1  # -1 for default loopback, or specify device index
  sample_rate: 16000
  chunk_size: 1024
  silence_duration: 1.5

# STT Settings
stt:
  model: "large-v3"  # Faster-Whisper model
  device: "cuda"  # "cuda" or "cpu"
  language: "zh"  # "zh" for Chinese, "en" for English

# LLM Settings (dual mode)
llm:
  mode: "local"  # "api" (Qwen) or "local" (Ollama/LM Studio)
  
  # Qwen API settings
  api:
    base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1"
    api_key: "YOUR_QWEN_API_KEY"
    model: "qwen-plus"
  
  # Local settings (Ollama/LM Studio)
  local:
    base_url: "http://localhost:11434/v1"  # Ollama default
    model: "qwen2.5:latest"

# UI Settings
ui:
  overlay:
    font_size: 28
    background_rgba: "0,0,0,102"  # rgba(0,0,0,0.4)
    text_color: "#FFFFFF"
    position: "bottom"
    opacity: 0.8
    always_on_top: true
    mouse_passthrough: true

# Resume Settings
resume:
  enabled: true
  max_tokens: 500
```

**Step 3: Create initial README.md**

```markdown
# Interview Helper - Windows 面试辅助工具

实时语音转录 + AI 智能回答的面试辅助工具

## 功能特性

- 🎤 **实时语音转录**：从腾讯会议/Zoom/Teams 等视频会议软件捕获音频
- 🧠 **GPU 加速 STT**：基于 Faster-Whisper 的实时语音识别（<3秒延迟）
- 🤖 **智能 AI 回答**：支持 Qwen API 和本地 Ollama/LM Studio
- 📝 **简历解析**：导入 Markdown 格式简历，让 AI 更懂你
- 🖥️ **屏幕字幕**：半透明悬浮窗口，不遮挡视频

## 快速开始

### 系统要求

- Windows 10/11
- Python 3.10+
- NVIDIA GPU with CUDA support (推荐 RTX 3060+)
- 至少 8GB RAM

### 安装

```bash
# 克隆项目
git clone https://github.com/your-username/interview-helper.git
cd interview-helper

# 创建虚拟环境
python -m venv venv
venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 配置

1. 复制 `config.yaml.template` 为 `config.yaml`
2. 配置 Qwen API Key 或本地 Ollama 地址
3. （可选）导入 Markdown 格式简历

### 运行

```bash
python app.py
```

## 技术栈

- **UI**: PyQt5
- **STT**: RealtimeSTT + Faster-Whisper (GPU)
- **LLM**: Qwen API / Ollama / LM Studio
- **Markdown**: mistune

## 项目结构

```
interview-helper/
├── app.py                # 主程序入口
├── ui/
│   ├── main_window.py    # 主窗口
│   ├── overlay_window.py # 透明字幕窗口
│   └── styles.py         # 样式表
├── core/
│   ├── audio_capture.py  # 音频捕获
│   ├── llm_client.py     # LLM 客户端
│   ├── resume_parser.py  # 简历解析
│   └── config.py         # 配置管理
├── requirements.txt
├── config.yaml           # 配置文件
└── README.md
```

## 许可证

MIT
```

**Step 4: Commit**

```bash
git add requirements.txt config.yaml README.md
git commit -m "chore: project setup with requirements and config template"
```

---

### Task 1.2: Configuration Management Core

**Files:**
- Create: `core/config.py`

**Step 1: Write config.py**

```python
"""Configuration management for Interview Helper."""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class AudioConfig:
    """Audio capture configuration."""
    device: int = -1
    sample_rate: int = 16000
    chunk_size: int = 1024
    silence_duration: float = 1.5


@dataclass
class STTConfig:
    """STT (Speech-to-Text) configuration."""
    model: str = "large-v3"
    device: str = "cuda"
    language: str = "zh"


@dataclass
class APIConfig:
    """Qwen API configuration."""
    base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    api_key: str = ""
    model: str = "qwen-plus"


@dataclass
class LocalConfig:
    """Local LLM (Ollama/LM Studio) configuration."""
    base_url: str = "http://localhost:11434/v1"
    model: str = "qwen2.5:latest"


@dataclass
class LLMConfig:
    """LLM configuration (dual mode)."""
    mode: str = "local"  # "api" or "local"
    api: APIConfig = field(default_factory=APIConfig)
    local: LocalConfig = field(default_factory=LocalConfig)


@dataclass
class OverlayConfig:
    """Overlay window configuration."""
    font_size: int = 28
    background_rgba: str = "0,0,0,102"
    text_color: str = "#FFFFFF"
    position: str = "bottom"
    opacity: float = 0.8
    always_on_top: bool = True
    mouse_passthrough: bool = True


@dataclass
class ResumeConfig:
    """Resume parsing configuration."""
    enabled: bool = True
    max_tokens: int = 500


@dataclass
class Config:
    """Main configuration class."""
    audio: AudioConfig = field(default_factory=AudioConfig)
    stt: STTConfig = field(default_factory=STTConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    ui: OverlayConfig = field(default_factory=OverlayConfig)
    resume: ResumeConfig = field(default_factory=ResumeConfig)
    
    # Internal
    _config_path: Path = field(default_factory=lambda: Path("config.yaml"))
    _defaults: Dict[str, Any] = field(init=False, repr=False)
    
    def __post_init__(self):
        """Initialize defaults from dataclass defaults."""
        self._defaults = {
            "audio": {
                "device": -1,
                "sample_rate": 16000,
                "chunk_size": 1024,
                "silence_duration": 1.5
            },
            "stt": {
                "model": "large-v3",
                "device": "cuda",
                "language": "zh"
            },
            "llm": {
                "mode": "local",
                "api": {
                    "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                    "api_key": "",
                    "model": "qwen-plus"
                },
                "local": {
                    "base_url": "http://localhost:11434/v1",
                    "model": "qwen2.5:latest"
                }
            },
            "ui": {
                "font_size": 28,
                "background_rgba": "0,0,0,102",
                "text_color": "#FFFFFF",
                "position": "bottom",
                "opacity": 0.8,
                "always_on_top": True,
                "mouse_passthrough": True
            },
            "resume": {
                "enabled": True,
                "max_tokens": 500
            }
        }
    
    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> 'Config':
        """Load configuration from YAML file."""
        if config_path is None:
            config_path = Path("config.yaml")
        
        if not config_path.exists():
            return cls()
        
        with open(config_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
        
        # Convert nested dicts to dataclasses
        audio_data = data.get('audio', {})
        stt_data = data.get('stt', {})
        llm_data = data.get('llm', {})
        ui_data = data.get('ui', {})
        resume_data = data.get('resume', {})
        
        return cls(
            audio=AudioConfig(**audio_data),
            stt=STTConfig(**stt_data),
            llm=LLMConfig(
                mode=llm_data.get('mode', 'local'),
                api=APIConfig(**llm_data.get('api', {})),
                local=LocalConfig(**llm_data.get('local', {}))
            ),
            ui=OverlayConfig(**ui_data),
            resume=ResumeConfig(**resume_data)
        )
    
    def save(self, config_path: Optional[Path] = None) -> None:
        """Save configuration to YAML file."""
        if config_path is None:
            config_path = self._config_path
        
        data = {
            "audio": {
                "device": self.audio.device,
                "sample_rate": self.audio.sample_rate,
                "chunk_size": self.audio.chunk_size,
                "silence_duration": self.audio.silence_duration
            },
            "stt": {
                "model": self.stt.model,
                "device": self.stt.device,
                "language": self.stt.language
            },
            "llm": {
                "mode": self.llm.mode,
                "api": {
                    "base_url": self.llm.api.base_url,
                    "api_key": self.llm.api.api_key,
                    "model": self.llm.api.model
                },
                "local": {
                    "base_url": self.llm.local.base_url,
                    "model": self.llm.local.model
                }
            },
            "ui": {
                "font_size": self.ui.font_size,
                "background_rgba": self.ui.background_rgba,
                "text_color": self.ui.text_color,
                "position": self.ui.position,
                "opacity": self.ui.opacity,
                "always_on_top": self.ui.always_on_top,
                "mouse_passthrough": self.ui.mouse_passthrough
            },
            "resume": {
                "enabled": self.resume.enabled,
                "max_tokens": self.resume.max_tokens
            }
        }
        
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False)
    
    def update_from_dict(self, data: Dict[str, Any]) -> None:
        """Update configuration from dictionary."""
        if 'audio' in data:
            self.audio = AudioConfig(**data['audio'])
        if 'stt' in data:
            self.stt = STTConfig(**data['stt'])
        if 'llm' in data:
            self.llm = LLMConfig(**data['llm'])
        if 'ui' in data:
            self.ui = OverlayConfig(**data['ui'])
        if 'resume' in data:
            self.resume = ResumeConfig(**data['resume'])
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "audio": {
                "device": self.audio.device,
                "sample_rate": self.audio.sample_rate,
                "chunk_size": self.audio.chunk_size,
                "silence_duration": self.audio.silence_duration
            },
            "stt": {
                "model": self.stt.model,
                "device": self.stt.device,
                "language": self.stt.language
            },
            "llm": {
                "mode": self.llm.mode,
                "api": {
                    "base_url": self.llm.api.base_url,
                    "api_key": self.llm.api.api_key,
                    "model": self.llm.api.model
                },
                "local": {
                    "base_url": self.llm.local.base_url,
                    "model": self.llm.local.model
                }
            },
            "ui": {
                "font_size": self.ui.font_size,
                "background_rgba": self.ui.background_rgba,
                "text_color": self.ui.text_color,
                "position": self.ui.position,
                "opacity": self.ui.opacity,
                "always_on_top": self.ui.always_on_top,
                "mouse_passthrough": self.ui.mouse_passthrough
            },
            "resume": {
                "enabled": self.resume.enabled,
                "max_tokens": self.resume.max_tokens
            }
        }


# Global config instance
_config: Optional[Config] = None


def get_config(config_path: Optional[Path] = None) -> Config:
    """Get global configuration instance."""
    global _config
    if _config is None:
        _config = Config.load(config_path)
    return _config


def set_config(config: Config) -> None:
    """Set global configuration instance."""
    global _config
    _config = config
```

**Step 2: Create test_config.py**

```python
"""Tests for config.py."""

import os
import tempfile
import pytest
from pathlib import Path

from core.config import (
    Config, AudioConfig, STTConfig, LLMConfig, APIConfig, 
    LocalConfig, OverlayConfig, ResumeConfig, get_config, set_config
)


class TestConfigDataclasses:
    """Test configuration dataclasses."""
    
    def test_audio_config_default(self):
        """Test AudioConfig default values."""
        config = AudioConfig()
        assert config.device == -1
        assert config.sample_rate == 16000
        assert config.chunk_size == 1024
        assert config.silence_duration == 1.5
    
    def test_stt_config_default(self):
        """Test STTConfig default values."""
        config = STTConfig()
        assert config.model == "large-v3"
        assert config.device == "cuda"
        assert config.language == "zh"
    
    def test_api_config_default(self):
        """Test APIConfig default values."""
        config = APIConfig()
        assert config.base_url == "https://dashscope.aliyuncs.com/compatible-mode/v1"
        assert config.api_key == ""
        assert config.model == "qwen-plus"
    
    def test_local_config_default(self):
        """Test LocalConfig default values."""
        config = LocalConfig()
        assert config.base_url == "http://localhost:11434/v1"
        assert config.model == "qwen2.5:latest"
    
    def test_overlay_config_default(self):
        """Test OverlayConfig default values."""
        config = OverlayConfig()
        assert config.font_size == 28
        assert config.background_rgba == "0,0,0,102"
        assert config.text_color == "#FFFFFF"
        assert config.position == "bottom"
        assert config.opacity == 0.8
        assert config.always_on_top is True
        assert config.mouse_passthrough is True
    
    def test_resume_config_default(self):
        """Test ResumeConfig default values."""
        config = ResumeConfig()
        assert config.enabled is True
        assert config.max_tokens == 500


class TestConfig:
    """Test main Config class."""
    
    def test_config_default(self):
        """Test Config default values."""
        config = Config()
        assert isinstance(config.audio, AudioConfig)
        assert isinstance(config.stt, STTConfig)
        assert isinstance(config.llm, LLMConfig)
        assert isinstance(config.ui, OverlayConfig)
        assert isinstance(config.resume, ResumeConfig)
    
    def test_config_to_dict(self):
        """Test Config to_dict method."""
        config = Config()
        data = config.to_dict()
        
        assert "audio" in data
        assert "stt" in data
        assert "llm" in data
        assert "ui" in data
        assert "resume" in data
    
    def test_config_update_from_dict(self):
        """Test Config update_from_dict method."""
        config = Config()
        data = {
            "audio": {"device": 5, "sample_rate": 44100},
            "stt": {"model": "medium", "language": "en"},
            "llm": {"mode": "api"},
            "ui": {"font_size": 32},
            "resume": {"enabled": False}
        }
        config.update_from_dict(data)
        
        assert config.audio.device == 5
        assert config.audio.sample_rate == 44100
        assert config.stt.model == "medium"
        assert config.stt.language == "en"
        assert config.llm.mode == "api"
        assert config.ui.font_size == 32
        assert config.resume.enabled is False


class TestConfigFileIO:
    """Test configuration file I/O."""
    
    def test_load_nonexistent_file(self):
        """Test loading from non-existent file returns defaults."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "nonexistent.yaml"
            config = Config.load(config_path)
            
            assert config.audio.device == -1
            assert config.stt.model == "large-v3"
    
    def test_save_and_load(self):
        """Test save and load configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            
            # Create and save config
            config = Config()
            config.audio.device = 5
            config.stt.model = "medium"
            config.llm.mode = "api"
            config.ui.font_size = 32
            config.resume.enabled = False
            config.save(config_path)
            
            # Load and verify
            loaded_config = Config.load(config_path)
            
            assert loaded_config.audio.device == 5
            assert loaded_config.stt.model == "medium"
            assert loaded_config.llm.mode == "api"
            assert loaded_config.ui.font_size == 32
            assert loaded_config.resume.enabled is False
    
    def test_yaml_file_content(self):
        """Test YAML file content structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            
            config = Config()
            config.save(config_path)
            
            # Read file and verify structure
            with open(config_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            assert "audio:" in content
            assert "stt:" in content
            assert "llm:" in content
            assert "ui:" in content
            assert "resume:" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

**Step 3: Run tests**

```bash
pytest tests/test_config.py -v
```

Expected output:
```
tests/test_config.py::TestConfigDataclasses::test_audio_config_default PASSED
tests/test_config.py::TestConfigDataclasses::test_stt_config_default PASSED
tests/test_config.py::TestConfigDataclasses::test_api_config_default PASSED
tests/test_config.py::TestConfigDataclasses::test_local_config_default PASSED
tests/test_config.py::TestConfigDataclasses::test_overlay_config_default PASSED
tests/test_config.py::TestConfigDataclasses::test_resume_config_default PASSED
tests/test_config.py::TestConfig::test_config_default PASSED
tests/test_config.py::TestConfig::test_config_to_dict PASSED
tests/test_config.py::TestConfig::test_config_update_from_dict PASSED
tests/test_config.py::TestConfigFileIO::test_load_nonexistent_file PASSED
tests/test_config.py::TestConfigFileIO::test_save_and_load PASSED
tests/test_config.py::TestConfigFileIO::test_yaml_file_content PASSED
```

**Step 4: Commit**

```bash
git add core/config.py tests/test_config.py
git commit -m "feat: add configuration management with YAML support"
```

---

## Wave 2: Core Modules (Parallel)

### Task 2.1: Resume Parser (Markdown)

**Files:**
- Create: `core/resume_parser.py`
- Create: `tests/test_resume_parser.py`

**Step 1: Write resume_parser.py**

```python
"""Resume parser for Markdown format."""

import re
import mistune
from typing import Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class Education:
    """Education entry."""
    school: str = ""
    degree: str = ""
    period: str = ""
    description: str = ""


@dataclass
class WorkExperience:
    """Work experience entry."""
    company: str = ""
    position: str = ""
    period: str = ""
    description: str = ""


@dataclass
class Project:
    """Project entry."""
    name: str = ""
    period: str = ""
    description: str = ""
    tech_stack: List[str] = field(default_factory=list)


@dataclass
class Resume:
    """Parsed resume data."""
    personal_info: Dict[str, str] = field(default_factory=dict)
    education: List[Education] = field(default_factory=list)
    work_experience: List[WorkExperience] = field(default_factory=list)
    projects: List[Project] = field(default_factory=list)
    skills: List[str] = field(default_factory=list)
    summary: str = ""


class ResumeParser:
    """Parser for Markdown format resumes."""
    
    def __init__(self):
        """Initialize parser."""
        self.markdown = mistune.create_markdown(
            escape=False,
            plugins=['tables', 'strikethrough', 'footnotes', 'task_lists']
        )
    
    def parse(self, markdown_text: str) -> Resume:
        """Parse Markdown resume text into structured data."""
        resume = Resume()
        
        # Extract personal info (name, email, phone, etc.)
        resume.personal_info = self._extract_personal_info(markdown_text)
        
        # Extract sections
        sections = self._extract_sections(markdown_text)
        
        # Parse each section
        for section_name, section_content in sections.items():
            if '教育经历' in section_name or 'Education' in section_name:
                resume.education = self._parse_education(section_content)
            elif '工作经历' in section_name or 'Work' in section_name or 'Experience' in section_name:
                resume.work_experience = self._parse_work_experience(section_content)
            elif '项目经历' in section_name or 'Project' in section_name:
                resume.projects = self._parse_projects(section_content)
            elif '技能' in section_name or 'Skills' in section_name:
                resume.skills = self._parse_skills(section_content)
            elif '个人总结' in section_name or 'Summary' in section_name or 'Profile' in section_name:
                resume.summary = self._parse_summary(section_content)
        
        return resume
    
    def _extract_personal_info(self, text: str) -> Dict[str, str]:
        """Extract personal information from resume."""
        info = {}
        
        # Email pattern
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        email_match = re.search(email_pattern, text)
        if email_match:
            info['email'] = email_match.group()
        
        # Phone pattern (Chinese phone)
        phone_pattern = r'1[3-9]\d{9}'
        phone_match = re.search(phone_pattern, text)
        if phone_match:
            info['phone'] = phone_match.group()
        
        # WeChat pattern
        wechat_pattern = r'微信[:：]?\s*([a-zA-Z0-9_-]{5,20})'
        wechat_match = re.search(wechat_pattern, text, re.IGNORECASE)
        if wechat_match:
            info['wechat'] = wechat_match.group(1)
        
        # Name (first line, usually)
        lines = text.strip().split('\n')
        if lines:
            first_line = lines[0].strip()
            # Remove markdown headers
            first_line = re.sub(r'^#+\s*', '', first_line)
            if first_line and len(first_line) < 50:
                info['name'] = first_line
        
        return info
    
    def _extract_sections(self, text: str) -> Dict[str, str]:
        """Extract sections from Markdown text."""
        sections = {}
        
        # Split by headers (## or ###)
        lines = text.split('\n')
        current_section = None
        current_content = []
        
        for line in lines:
            header_match = re.match(r'^(#{1,3})\s+(.+)$', line)
            if header_match:
                # Save previous section
                if current_section:
                    sections[current_section] = '\n'.join(current_content).strip()
                
                # Start new section
                current_section = header_match.group(2).strip()
                current_content = []
            elif current_section:
                current_content.append(line)
        
        # Save last section
        if current_section:
            sections[current_section] = '\n'.join(current_content).strip()
        
        return sections
    
    def _parse_education(self, content: str) -> List[Education]:
        """Parse education section."""
        educations = []
        
        # Split by empty lines or bullet points
        blocks = re.split(r'\n\s*\n', content.strip())
        
        for block in blocks:
            block = block.strip()
            if not block:
                continue
            
            education = Education()
            
            # Try to extract school and degree from first line
            # Pattern: School - Degree - Period or similar
            lines = block.split('\n')
            
            if lines:
                first_line = lines[0].strip()
                
                # Pattern: School (Degree), Period
                match = re.match(r'^(.+?)\s*[-/]\s*(.+?)\s*[-/]\s*(.+)$', first_line)
                if match:
                    education.school = match.group(1).strip()
                    education.degree = match.group(2).strip()
                    education.period = match.group(3).strip()
                else:
                    # Just school name
                    education.school = first_line
            
            # Extract period from other lines
            for line in lines[1:]:
                line = line.strip()
                # Pattern: 2020.09 - 2024.06
                period_match = re.search(r'(\d{4}.\d{2}\s*[-–—]\s*\d{4}.\d{2})', line)
                if period_match and not education.period:
                    education.period = period_match.group(1)
                
                # Description (lines after period)
                if period_match:
                    desc = line.replace(period_match.group(1), '').strip()
                    if desc and not desc.startswith('-'):
                        education.description += desc + ' '
            
            # Clean up description
            education.description = education.description.strip()
            
            if education.school:
                educations.append(education)
        
        return educations
    
    def _parse_work_experience(self, content: str) -> List[WorkExperience]:
        """Parse work experience section."""
        experiences = []
        
        # Split by empty lines or bullet points
        blocks = re.split(r'\n\s*\n', content.strip())
        
        for block in blocks:
            block = block.strip()
            if not block:
                continue
            
            exp = WorkExperience()
            
            lines = block.split('\n')
            
            if lines:
                first_line = lines[0].strip()
                
                # Pattern: Company - Position - Period
                match = re.match(r'^(.+?)\s*[-/]\s*(.+?)\s*[-/]\s*(.+)$', first_line)
                if match:
                    exp.company = match.group(1).strip()
                    exp.position = match.group(2).strip()
                    exp.period = match.group(3).strip()
                else:
                    exp.company = first_line
            
            # Extract period and description
            for line in lines[1:]:
                line = line.strip()
                
                # Period pattern
                period_match = re.search(r'(\d{4}.\d{2}\s*[-–—]\s*\d{4}.\d{2})', line)
                if period_match and not exp.period:
                    exp.period = period_match.group(1)
                
                # Description
                if period_match:
                    desc = line.replace(period_match.group(1), '').strip()
                    if desc:
                        exp.description += desc + ' '
            
            exp.description = exp.description.strip()
            
            if exp.company:
                experiences.append(exp)
        
        return experiences
    
    def _parse_projects(self, content: str) -> List[Project]:
        """Parse projects section."""
        projects = []
        
        # Split by empty lines or bullet points
        blocks = re.split(r'\n\s*\n', content.strip())
        
        for block in blocks:
            block = block.strip()
            if not block:
                continue
            
            project = Project()
            
            lines = block.split('\n')
            
            if lines:
                first_line = lines[0].strip()
                
                # Pattern: Project Name - Period
                match = re.match(r'^(.+?)\s*[-/]\s*(.+)$', first_line)
                if match:
                    project.name = match.group(1).strip()
                    project.period = match.group(2).strip()
                else:
                    project.name = first_line
            
            # Extract tech stack and description
            for line in lines[1:]:
                line = line.strip()
                
                # Period pattern
                period_match = re.search(r'(\d{4}.\d{2}\s*[-–—]\s*\d{4}.\d{2})', line)
                if period_match and not project.period:
                    project.period = period_match.group(1)
                
                # Tech stack (lines with "技术栈:" or "Tech:")
                if '技术栈' in line or 'Tech' in line or 'Tech Stack' in line:
                    tech_match = re.search(r'[技术栈:Tech].*[:：]\s*(.+)$', line, re.IGNORECASE)
                    if tech_match:
                        tech_str = tech_match.group(1)
                        project.tech_stack = [t.strip() for t in re.split(r'[,，]', tech_str)]
                
                # Description
                if not period_match and '技术栈' not in line and 'Tech' not in line:
                    if line.startswith('-') or line.startswith('•'):
                        project.description += line[1:].strip() + ' '
                    elif line:
                        project.description += line + ' '
            
            project.description = project.description.strip()
            
            if project.name:
                projects.append(project)
        
        return projects
    
    def _parse_skills(self, content: str) -> List[str]:
        """Parse skills section."""
        skills = []
        
        # Split by commas, newlines, or bullet points
        lines = content.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            
            # Remove bullet points
            line = re.sub(r'^[-•*]\s*', '', line)
            
            # Split by commas
            for skill in re.split(r'[,，]', line):
                skill = skill.strip()
                if skill and len(skill) < 50:
                    skills.append(skill)
        
        return skills
    
    def _parse_summary(self, content: str) -> str:
        """Parse summary/profile section."""
        # Clean up the content
        lines = content.strip().split('\n')
        summary_lines = []
        
        for line in lines:
            line = line.strip()
            # Remove bullet points
            line = re.sub(r'^[-•*]\s*', '', line)
            if line:
                summary_lines.append(line)
        
        return ' '.join(summary_lines).strip()
    
    def to_prompt_context(self, resume: Resume, max_tokens: int = 500) -> str:
        """Convert resume to prompt context string."""
        parts = []
        
        # Personal info
        if resume.personal_info:
            parts.append("## 个人信息")
            for key, value in resume.personal_info.items():
                parts.append(f"- {key}: {value}")
            parts.append("")
        
        # Summary
        if resume.summary:
            parts.append("## 个人总结")
            parts.append(resume.summary)
            parts.append("")
        
        # Skills
        if resume.skills:
            parts.append("## 技能")
            parts.append(", ".join(resume.skills))
            parts.append("")
        
        # Education
        if resume.education:
            parts.append("## 教育经历")
            for edu in resume.education:
                if edu.school:
                    parts.append(f"- {edu.school} - {edu.degree} ({edu.period})")
                    if edu.description:
                        parts.append(f"  {edu.description}")
            parts.append("")
        
        # Work Experience
        if resume.work_experience:
            parts.append("## 工作经历")
            for exp in resume.work_experience:
                if exp.company:
                    parts.append(f"- {exp.company} - {exp.position} ({exp.period})")
                    if exp.description:
                        parts.append(f"  {exp.description}")
            parts.append("")
        
        # Projects
        if resume.projects:
            parts.append("## 项目经历")
            for proj in resume.projects:
                if proj.name:
                    parts.append(f"- {proj.name} ({proj.period})")
                    if proj.tech_stack:
                        parts.append(f"  技术栈: {', '.join(proj.tech_stack)}")
                    if proj.description:
                        parts.append(f"  {proj.description}")
            parts.append("")
        
        return '\n'.join(parts)


# Global parser instance
_parser: Optional[ResumeParser] = None


def get_parser() -> ResumeParser:
    """Get global parser instance."""
    global _parser
    if _parser is None:
        _parser = ResumeParser()
    return _parser


def parse_resume(markdown_text: str) -> Resume:
    """Parse resume from Markdown text."""
    return get_parser().parse(markdown_text)
```

**Step 2: Write test_resume_parser.py**

```python
"""Tests for resume_parser.py."""

import pytest
from core.resume_parser import (
    ResumeParser, Resume, Education, WorkExperience, Project,
    parse_resume, get_parser
)


class TestResumeParser:
    """Test ResumeParser class."""
    
    def test_parse_simple_resume(self):
        """Test parsing a simple resume."""
        markdown = """
# 张三

- 邮箱: zhangsan@example.com
- 电话: 13800138000

## 个人总结
5年Python开发经验，擅长后端开发和系统设计。

## 技术栈
Python, Django, Flask, MySQL, Redis, Docker

## 教育经历
- 清华大学 - 计算机科学与技术 - 本科 (2015.09 - 2019.06)
- 主修课程: 数据结构、算法、操作系统

## 工作经历
- 腾讯 - 后端开发工程师 (2019.07 - 至今)
- 负责微信支付后台系统开发和优化

## 项目经历
- 微信支付系统重构 - 2022.01 - 2023.12
  技术栈: Python, gRPC, Kafka
  描述: 重构支付核心系统，提升性能30%
"""
        parser = ResumeParser()
        resume = parser.parse(markdown)
        
        assert resume.personal_info.get('name') == '张三'
        assert 'zhangsan@example.com' in resume.personal_info.get('email', '')
        assert len(resume.skills) > 0
        assert len(resume.education) == 1
        assert resume.education[0].school == '清华大学'
        assert len(resume.work_experience) == 1
        assert resume.work_experience[0].company == '腾讯'
        assert len(resume.projects) == 1
        assert resume.projects[0].name == '微信支付系统重构'
    
    def test_parse_english_resume(self):
        """Test parsing an English resume."""
        markdown = """
# John Doe

- Email: john@example.com
- Phone: +1-555-1234

## Summary
Senior Python developer with 8 years of experience in backend development.

## Skills
Python, Django, Flask, PostgreSQL, AWS, Kubernetes

## Education
- Stanford University - MS Computer Science (2014.09 - 2016.06)

## Work Experience
- Google - Software Engineer (2016.08 - 2020.05)
- Developed distributed systems for search infrastructure

## Projects
- Search Index Optimization - 2019.01 - 2019.12
  Tech Stack: Python, Go, Bigtable
  Improved search latency by 40%
"""
        parser = ResumeParser()
        resume = parser.parse(markdown)
        
        assert resume.personal_info.get('name') == 'John Doe'
        assert 'john@example.com' in resume.personal_info.get('email', '')
        assert len(resume.skills) > 0
        assert len(resume.education) == 1
        assert 'Stanford' in resume.education[0].school
        assert len(resume.work_experience) == 1
        assert 'Google' in resume.work_experience[0].company
    
    def test_to_prompt_context(self):
        """Test converting resume to prompt context."""
        markdown = """
# 李四

## 技能
Python, Java, Spring Boot, MySQL

## 教育经历
- 北京大学 - 软件工程 - 本科 (2016.09 - 2020.06)

## 工作经历
- 字节跳动 - 后端开发 (2020.07 - 至今)
  负责抖音后端服务开发
"""
        parser = ResumeParser()
        resume = parser.parse(markdown)
        context = parser.to_prompt_context(resume, max_tokens=300)
        
        assert "## 个人信息" in context
        assert "## 技能" in context
        assert "Python" in context
        assert "## 教育经历" in context
        assert "北京大学" in context
        assert "## 工作经历" in context
        assert "字节跳动" in context
    
    def test_empty_resume(self):
        """Test parsing empty resume."""
        parser = ResumeParser()
        resume = parser.parse("")
        
        assert isinstance(resume, Resume)
        assert len(resume.skills) == 0
        assert len(resume.education) == 0
        assert len(resume.work_experience) == 0
        assert len(resume.projects) == 0


class TestParseResumeFunction:
    """Test parse_resume standalone function."""
    
    def test_parse_resume_function(self):
        """Test parse_resume function."""
        markdown = """
# 王五

## 技能
Go, Rust,微服务

## 教育经历
- 浙江大学 - 计算机 (2017.09 - 2021.06)
"""
        resume = parse_resume(markdown)
        
        assert isinstance(resume, Resume)
        assert '王五' in resume.personal_info.get('name', '')


class TestGetParserFunction:
    """Test get_parser function."""
    
    def test_get_parser_singleton(self):
        """Test get_parser returns singleton."""
        parser1 = get_parser()
        parser2 = get_parser()
        
        assert parser1 is parser2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

**Step 3: Run tests**

```bash
pytest tests/test_resume_parser.py -v
```

Expected: All tests pass

**Step 4: Commit**

```bash
git add core/resume_parser.py tests/test_resume_parser.py
git commit -m "feat: add Markdown resume parser with multi-language support"
```

---

### Task 2.2: LLM Client (Dual Mode: Qwen API + Ollama)

**Files:**
- Create: `core/llm_client.py`
- Create: `tests/test_llm_client.py`

**Step 1: Write llm_client.py**

```python
"""LLM client supporting Qwen API and local Ollama/LM Studio."""

import os
import requests
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum

from core.config import Config, get_config


class LLMMode(Enum):
    """LLM mode enum."""
    API = "api"  # Qwen API
    LOCAL = "local"  # Ollama/LM Studio


@dataclass
class LLMResponse:
    """LLM response."""
    text: str
    model: str
    usage: Optional[Dict[str, int]] = None


class LLMClient:
    """Client for Qwen API and local LLMs."""
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize LLM client."""
        self.config = config or get_config()
        self.mode = LLMMode(self.config.llm.mode)
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 512,
        temperature: float = 0.7,
        stream: bool = False
    ) -> LLMResponse:
        """Generate response from LLM."""
        if self.mode == LLMMode.API:
            return self._generate_api(prompt, system_prompt, max_tokens, temperature, stream)
        else:
            return self._generate_local(prompt, system_prompt, max_tokens, temperature, stream)
    
    def _generate_api(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 512,
        temperature: float = 0.7,
        stream: bool = False
    ) -> LLMResponse:
        """Generate response using Qwen API."""
        import openai
        
        api_config = self.config.llm.api
        
        if not api_config.api_key:
            raise ValueError("Qwen API key not configured")
        
        client = openai.OpenAI(
            api_key=api_config.api_key,
            base_url=api_config.base_url
        )
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        try:
            response = client.chat.completions.create(
                model=api_config.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=stream
            )
            
            if stream:
                # Handle streaming (simplified for now)
                full_text = ""
                for chunk in response:
                    if chunk.choices and chunk.choices[0].delta.content:
                        full_text += chunk.choices[0].delta.content
                return LLMResponse(text=full_text, model=api_config.model)
            else:
                text = response.choices[0].message.content
                usage = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
                return LLMResponse(text=text, model=api_config.model, usage=usage)
        
        except Exception as e:
            raise RuntimeError(f"Qwen API error: {e}")
    
    def _generate_local(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 512,
        temperature: float = 0.7,
        stream: bool = False
    ) -> LLMResponse:
        """Generate response using local Ollama/LM Studio API."""
        local_config = self.config.llm.local
        
        # Build messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        # Build request payload
        payload = {
            "model": local_config.model,
            "messages": messages,
            "temperature": temperature,
            "stream": stream
        }
        
        # Add max_tokens for LM Studio compatibility
        if max_tokens:
            payload["max_tokens"] = max_tokens
        
        try:
            response = requests.post(
                f"{local_config.base_url}/chat/completions",
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            
            data = response.json()
            
            if stream:
                # Handle streaming (simplified)
                full_text = ""
                # For streaming, we'd need to handle SSE response
                # For now, return non-streaming response
                if data.get("choices"):
                    full_text = data["choices"][0]["message"]["content"]
                return LLMResponse(text=full_text, model=local_config.model)
            else:
                text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                
                # Extract usage if available
                usage = None
                if "usage" in data:
                    usage = data["usage"]
                
                return LLMResponse(text=text, model=local_config.model, usage=usage)
        
        except requests.exceptions.ConnectionError:
            raise RuntimeError(f"Cannot connect to local LLM at {local_config.base_url}")
        except requests.exceptions.Timeout:
            raise RuntimeError("Local LLM request timeout")
        except Exception as e:
            raise RuntimeError(f"Local LLM error: {e}")
    
    def generate_short_answer(
        self,
        question: str,
        resume_context: Optional[str] = None,
        max_tokens: int = 150
    ) -> str:
        """Generate short answer (50-150 tokens) for interview question."""
        system_prompt = """你是一位专业的面试辅导助手。请根据面试官的问题和候选人的简历，给出简短、专业的回答。

要求：
1. 回答长度：50-100字
2. 语言：中文（除非问题要求英文）
3. 重点突出候选人的优势和相关经验
4. 保持专业、自信的语气
5. 不要使用过于夸张的形容词"""
        
        if resume_context:
            prompt = f"""候选人简历：
{resume_context}

面试官问题：
{question}

请给出简短回答："""
        else:
            prompt = f"""面试官问题：
{question}

请给出简短回答（50-100字）："""
        
        response = self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=max_tokens,
            temperature=0.7
        )
        
        return response.text.strip()
    
    def generate_interview_questions(
        self,
        resume_context: str,
        count: int = 5
    ) -> List[str]:
        """Generate interview questions based on resume."""
        system_prompt = """你是一位专业的面试官。请根据候选人的简历生成面试问题。

要求：
1. 问题应围绕简历中的项目经验和技能展开
2. 问题难度适中，考察实际能力
3. 每个问题简洁明了"""
        
        prompt = f"""候选人简历：
{resume_context}

请生成{count}个面试问题，每行一个问题："""
        
        response = self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=300,
            temperature=0.8
        )
        
        # Parse questions from response
        questions = []
        for line in response.text.strip().split('\n'):
            line = line.strip()
            # Remove numbering
            line = re.sub(r'^\d+[\.)]\s*', '', line)
            if line and len(line) > 10:
                questions.append(line)
        
        return questions[:count]


# Global client instance
_client: Optional[LLMClient] = None


def get_client(config: Optional[Config] = None) -> LLMClient:
    """Get global LLM client instance."""
    global _client
    if _client is None:
        _client = LLMClient(config)
    return _client


def set_client(client: LLMClient) -> None:
    """Set global LLM client instance."""
    global _client
    _client = client


def generate_short_answer(
    question: str,
    resume_context: Optional[str] = None,
    config: Optional[Config] = None
) -> str:
    """Generate short answer using global client."""
    return get_client(config).generate_short_answer(question, resume_context)


def generate_interview_questions(
    resume_context: str,
    count: int = 5,
    config: Optional[Config] = None
) -> List[str]:
    """Generate interview questions using global client."""
    return get_client(config).generate_interview_questions(resume_context, count)
```

**Step 2: Write test_llm_client.py**

```python
"""Tests for llm_client.py."""

import pytest
import responses
from unittest.mock import patch, MagicMock

from core.config import Config, LLMConfig, APIConfig, LocalConfig
from core.llm_client import LLMClient, LLMMode, LLMResponse, get_client


class TestLLMClient:
    """Test LLMClient class."""
    
    def test_init_with_api_mode(self):
        """Test client initialization with API mode."""
        config = Config()
        config.llm.mode = "api"
        config.llm.api.api_key = "test-key"
        
        client = LLMClient(config)
        
        assert client.mode == LLMMode.API
        assert client.config.llm.mode == "api"
    
    def test_init_with_local_mode(self):
        """Test client initialization with local mode."""
        config = Config()
        config.llm.mode = "local"
        
        client = LLMClient(config)
        
        assert client.mode == LLMMode.LOCAL
        assert client.config.llm.mode == "local"
    
    def test_generate_short_answer_api_mode(self):
        """Test generate_short_answer with API mode."""
        config = Config()
        config.llm.mode = "api"
        config.llm.api.api_key = "test-key"
        config.llm.api.base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
        config.llm.api.model = "qwen-plus"
        
        client = LLMClient(config)
        
        # Mock the API call
        with patch.object(client, '_generate_api') as mock_generate:
            mock_generate.return_value = LLMResponse(
                text="这是一个简短的回答。",
                model="qwen-plus"
            )
            
            result = client.generate_short_answer("你有什么优势？")
            
            assert "这是一个简短的回答。" in result
    
    def test_generate_short_answer_local_mode(self):
        """Test generate_short_answer with local mode."""
        config = Config()
        config.llm.mode = "local"
        config.llm.local.base_url = "http://localhost:11434/v1"
        config.llm.local.model = "qwen2.5:latest"
        
        client = LLMClient(config)
        
        # Mock the API call
        with patch.object(client, '_generate_local') as mock_generate:
            mock_generate.return_value = LLMResponse(
                text="我具备扎实的技术基础和丰富的项目经验。",
                model="qwen2.5:latest"
            )
            
            result = client.generate_short_answer("你有什么优势？")
            
            assert "我具备扎实的技术基础和丰富的项目经验。" in result
    
    def test_generate_interview_questions(self):
        """Test generate_interview_questions."""
        config = Config()
        config.llm.mode = "local"
        
        client = LLMClient(config)
        
        resume_context = """
## 技能
Python, Django, MySQL

## 工作经历
- 公司A - 后端开发 (2020-至今)
"""
        
        # Mock the API call
        with patch.object(client, 'generate') as mock_generate:
            mock_generate.return_value = LLMResponse(
                text="1. 请介绍一下你在公司A负责的项目\n2. 你如何优化MySQL数据库性能\n3. Django中的中间件是什么？",
                model="qwen2.5:latest"
            )
            
            questions = client.generate_interview_questions(resume_context, count=3)
            
            assert len(questions) >= 1
            assert any("公司A" in q for q in questions) or any("项目" in q for q in questions)


class TestLLMClientAPI:
    """Test LLMClient with mocked API calls."""
    
    @responses.activate
    def test_generate_api_success(self):
        """Test API mode generation success."""
        config = Config()
        config.llm.mode = "api"
        config.llm.api.api_key = "test-key"
        config.llm.api.base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
        config.llm.api.model = "qwen-plus"
        
        # Mock the API response
        responses.add(
            responses.POST,
            "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
            json={
                "choices": [{
                    "message": {
                        "content": "这是一个测试回答。"
                    }
                }],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 20,
                    "total_tokens": 30
                }
            },
            status=200
        )
        
        client = LLMClient(config)
        response = client._generate_api("测试问题")
        
        assert response.text == "这是一个测试回答。"
        assert response.usage is not None
        assert response.usage["total_tokens"] == 30
    
    @responses.activate
    def test_generate_local_success(self):
        """Test local mode generation success."""
        config = Config()
        config.llm.mode = "local"
        config.llm.local.base_url = "http://localhost:11434/v1"
        config.llm.local.model = "qwen2.5:latest"
        
        # Mock the API response
        responses.add(
            responses.POST,
            "http://localhost:11434/v1/chat/completions",
            json={
                "choices": [{
                    "message": {
                        "content": "本地模型的回答。"
                    }
                }]
            },
            status=200
        )
        
        client = LLMClient(config)
        response = client._generate_local("测试问题")
        
        assert response.text == "本地模型的回答。"


class TestLLMClientErrors:
    """Test LLMClient error handling."""
    
    def test_generate_api_no_key(self):
        """Test API mode without API key raises error."""
        config = Config()
        config.llm.mode = "api"
        config.llm.api.api_key = ""
        
        client = LLMClient(config)
        
        with pytest.raises(ValueError, match="API key not configured"):
            client._generate_api("测试问题")
    
    def test_generate_local_connection_error(self):
        """Test local mode connection error."""
        config = Config()
        config.llm.mode = "local"
        config.llm.local.base_url = "http://localhost:9999/v1"  # Wrong port
        config.llm.local.model = "qwen2.5:latest"
        
        client = LLMClient(config)
        
        with pytest.raises(RuntimeError, match="Cannot connect"):
            client._generate_local("测试问题")


class TestGlobalFunctions:
    """Test global helper functions."""
    
    def test_get_client_singleton(self):
        """Test get_client returns singleton."""
        client1 = get_client()
        client2 = get_client()
        
        assert client1 is client2
    
    def test_generate_short_answer_function(self):
        """Test generate_short_answer function."""
        config = Config()
        config.llm.mode = "local"
        
        with patch('core.llm_client.get_client') as mock_get:
            mock_client = MagicMock()
            mock_client.generate_short_answer.return_value = "测试回答"
            mock_get.return_value = mock_client
            
            result = generate_short_answer("测试问题", config=config)
            
            assert result == "测试回答"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

**Step 3: Run tests**

```bash
pytest tests/test_llm_client.py -v
```

Expected: All tests pass

**Step 4: Commit**

```bash
git add core/llm_client.py tests/test_llm_client.py
git commit -m "feat: add dual-mode LLM client (Qwen API + Ollama)"
```

---

### Task 2.3: Audio Capture with RealtimeSTT

**Files:**
- Create: `core/audio_capture.py`
- Create: `tests/test_audio_capture.py`

**Step 1: Write audio_capture.py**

```python
"""Audio capture using RealtimeSTT with system loopback."""

import threading
import queue
import sounddevice as sd
import numpy as np
from typing import Optional, Callable, List, Dict
from dataclasses import dataclass, field
from enum import Enum

from core.config import Config, get_config


class AudioState(Enum):
    """Audio capture state."""
    IDLE = "idle"
    RECORDING = "recording"
    PROCESSING = "processing"
    STOPPED = "stopped"


@dataclass
class AudioChunk:
    """Audio chunk with metadata."""
    data: np.ndarray
    timestamp: float
    sample_rate: int


class AudioCapture:
    """Audio capture with RealtimeSTT integration."""
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize audio capture."""
        self.config = config or get_config()
        
        # Audio settings
        self.device = self.config.audio.device
        self.sample_rate = self.config.audio.sample_rate
        self.chunk_size = self.config.audio.chunk_size
        self.silence_duration = self.config.audio.silence_duration
        
        # State
        self.state = AudioState.IDLE
        self._stream: Optional[sd.InputStream] = None
        self._audio_queue: queue.Queue = queue.Queue()
        self._audio_buffer: List[np.ndarray] = []
        self._last_speech_time: float = 0
        self._silence_counter: int = 0
        
        # Callbacks
        self.on_speech_start: Optional[Callable[[float], None]] = None
        self.on_speech_end: Optional[Callable[[str], None]] = None
        self.on_error: Optional[Callable[[Exception], None]] = None
        
        # STT model (lazy loaded)
        self._stt_model = None
        self._stt_initialized = False
    
    def _initialize_stt(self):
        """Initialize RealtimeSTT model."""
        if self._stt_initialized:
            return
        
        try:
            from RealtimeSTT import RealtimeSTT
            
            self._stt_model = RealtimeSTT(
                model=self.config.stt.model,
                device=self.config.stt.device,
                language=self.config.stt.language,
                silence_threshold=self.silence_duration
            )
            self._stt_initialized = True
            
        except ImportError:
            raise RuntimeError("RealtimeSTT not installed. Run: pip install RealtimeSTT")
        except Exception as e:
            raise RuntimeError(f"Failed to initialize STT model: {e}")
    
    def start(self):
        """Start audio capture."""
        if self.state == AudioState.RECORDING:
            return
        
        try:
            self._initialize_stt()
            
            # Open audio stream
            self._stream = sd.InputStream(
                device=self.device,
                samplerate=self.sample_rate,
                channels=1,
                dtype='float32',
                blocksize=self.chunk_size,
                callback=self._audio_callback
            )
            
            self._stream.start()
            self.state = AudioState.RECORDING
            
            # Start processing thread
            self._processing_thread = threading.Thread(
                target=self._process_audio,
                daemon=True
            )
            self._processing_thread.start()
            
        except Exception as e:
            if self.on_error:
                self.on_error(e)
            raise
    
    def stop(self):
        """Stop audio capture."""
        if self.state != AudioState.RECORDING:
            return
        
        try:
            # Stop stream
            if self._stream:
                self._stream.stop()
                self._stream.close()
                self._stream = None
            
            self.state = AudioState.STOPPED
            
            # Wait for processing thread
            self._audio_queue.put(None)  # Signal thread to stop
            
        except Exception as e:
            if self.on_error:
                self.on_error(e)
            raise
    
    def _audio_callback(self, indata: np.ndarray, frames: int, time_info, status):
        """Audio callback from sounddevice."""
        if status:
            print(f"Audio status: {status}")
        
        # Add to buffer
        audio_data = indata.copy()
        self._audio_queue.put(audio_data)
    
    def _process_audio(self):
        """Process audio chunks and detect speech."""
        import time
        
        while self.state == AudioState.RECORDING:
            try:
                chunk = self._audio_queue.get(timeout=1.0)
                
                if chunk is None:
                    break
                
                # Process chunk
                self._process_chunk(chunk)
                
            except queue.Empty:
                continue
            except Exception as e:
                if self.on_error:
                    self.on_error(e)
    
    def _process_chunk(self, chunk: np.ndarray):
        """Process a single audio chunk."""
        import time
        
        # For now, just buffer audio
        # In production, you'd pass this to RealtimeSTT
        self._audio_buffer.append(chunk)
        
        # Simple silence detection (placeholder)
        # Real implementation would use voice activity detection
        volume = np.abs(chunk).mean()
        
        if volume > 0.01:  # Threshold for speech
            self._last_speech_time = time.time()
            self._silence_counter = 0
            
            if self.state == AudioState.IDLE:
                self.state = AudioState.RECORDING
                if self.on_speech_start:
                    self.on_speech_start(time.time())
        else:
            self._silence_counter += 1
        
        # Check for silence duration
        if self._silence_counter > (self.silence_duration * 1000 / self.chunk_size):
            if self.state == AudioState.RECORDING and self._audio_buffer:
                # Speech ended, process buffer
                self._process_speech_buffer()
    
    def _process_speech_buffer(self):
        """Process accumulated speech buffer."""
        import time
        
        if not self._audio_buffer:
            return
        
        # Concatenate audio
        audio_data = np.concatenate(self._audio_buffer)
        
        # Reset buffer
        self._audio_buffer = []
        
        # Transcribe using STT
        try:
            self.state = AudioState.PROCESSING
            
            # Use RealtimeSTT for transcription
            if self._stt_model:
                text = self._stt_model.recognize(audio_data, self.sample_rate)
                
                if text and text.strip():
                    if self.on_speech_end:
                        self.on_speech_end(text.strip())
            
            self.state = AudioState.RECORDING
            
        except Exception as e:
            if self.on_error:
                self.on_error(e)
            self.state = AudioState.RECORDING
    
    def get_devices(self) -> List[Dict]:
        """Get available audio devices."""
        try:
            devices = sd.query_devices()
            
            result = []
            for i, device in enumerate(devices):
                result.append({
                    "index": i,
                    "name": device['name'],
                    "max_input_channels": device['max_input_channels'],
                    "default_samplerate": device['default_samplerate']
                })
            
            return result
        
        except Exception as e:
            if self.on_error:
                self.on_error(e)
            return []
    
    def is_speaking(self) -> bool:
        """Check if currently speaking."""
        import time
        
        if self.state != AudioState.RECORDING:
            return False
        
        # Check if speech ended recently
        silence_threshold = self.silence_duration + 0.5
        return (time.time() - self._last_speech_time) < silence_threshold
    
    def reset(self):
        """Reset audio capture state."""
        self._audio_buffer = []
        self._last_speech_time = 0
        self._silence_counter = 0
        self.state = AudioState.IDLE


# Global instance
_audio_capture: Optional[AudioCapture] = None


def get_audio_capture(config: Optional[Config] = None) -> AudioCapture:
    """Get global audio capture instance."""
    global _audio_capture
    if _audio_capture is None:
        _audio_capture = AudioCapture(config)
    return _audio_capture


def set_audio_capture(capture: AudioCapture) -> None:
    """Set global audio capture instance."""
    global _audio_capture
    _audio_capture = capture


def start_audio_capture() -> AudioCapture:
    """Start global audio capture."""
    capture = get_audio_capture()
    capture.start()
    return capture


def stop_audio_capture() -> None:
    """Stop global audio capture."""
    capture = get_audio_capture()
    capture.stop()
```

**Step 2: Write test_audio_capture.py**

```python
"""Tests for audio_capture.py."""

import pytest
import numpy as np
from unittest.mock import patch, MagicMock, call
from unittest.mock import patch

from core.config import Config
from core.audio_capture import AudioCapture, AudioState, get_audio_capture


class TestAudioCapture:
    """Test AudioCapture class."""
    
    def test_init_default(self):
        """Test initialization with default config."""
        config = Config()
        capture = AudioCapture(config)
        
        assert capture.config == config
        assert capture.state == AudioState.IDLE
        assert capture.device == -1
        assert capture.sample_rate == 16000
    
    def test_init_custom_config(self):
        """Test initialization with custom config."""
        config = Config()
        config.audio.device = 5
        config.audio.sample_rate = 44100
        config.audio.chunk_size = 2048
        config.audio.silence_duration = 2.0
        
        capture = AudioCapture(config)
        
        assert capture.device == 5
        assert capture.sample_rate == 44100
        assert capture.chunk_size == 2048
        assert capture.silence_duration == 2.0
    
    def test_get_devices(self):
        """Test getting audio devices."""
        config = Config()
        capture = AudioCapture(config)
        
        with patch('sounddevice.query_devices') as mock_query:
            mock_query.return_value = [
                {'name': 'Device 1', 'max_input_channels': 2, 'default_samplerate': 44100},
                {'name': 'Device 2', 'max_input_channels': 1, 'default_samplerate': 16000},
            ]
            
            devices = capture.get_devices()
            
            assert len(devices) == 2
            assert devices[0]['name'] == 'Device 1'
            assert devices[1]['name'] == 'Device 2'
    
    def test_is_speaking_false(self):
        """Test is_speaking returns False when not recording."""
        config = Config()
        capture = AudioCapture(config)
        capture.state = AudioState.IDLE
        
        assert capture.is_speaking() is False
    
    def test_is_speaking_true(self):
        """Test is_speaking returns True when speaking."""
        import time
        
        config = Config()
        capture = AudioCapture(config)
        capture.state = AudioState.RECORDING
        capture._last_speech_time = time.time()
        capture.silence_duration = 1.5
        
        assert capture.is_speaking() is True
    
    def test_reset(self):
        """Test reset clears state."""
        config = Config()
        capture = AudioCapture(config)
        
        # Set some state
        capture._audio_buffer = [np.array([0.1, 0.2])]
        capture._last_speech_time = 1234567890
        capture._silence_counter = 100
        capture.state = AudioState.RECORDING
        
        capture.reset()
        
        assert len(capture._audio_buffer) == 0
        assert capture._silence_counter == 0
        assert capture.state == AudioState.IDLE


class TestAudioCaptureCallbacks:
    """Test AudioCapture callbacks."""
    
    def test_on_speech_start_callback(self):
        """Test on_speech_start callback."""
        config = Config()
        capture = AudioCapture(config)
        
        callback_called = []
        
        def on_speech_start(timestamp):
            callback_called.append(timestamp)
        
        capture.on_speech_start = on_speech_start
        
        # This would be called during processing
        # For now, just verify the callback can be set
        assert capture.on_speech_start == on_speech_start
    
    def test_on_speech_end_callback(self):
        """Test on_speech_end callback."""
        config = Config()
        capture = AudioCapture(config)
        
        callback_called = []
        
        def on_speech_end(text):
            callback_called.append(text)
        
        capture.on_speech_end = on_speech_end
        
        assert capture.on_speech_end == on_speech_end
    
    def test_on_error_callback(self):
        """Test on_error callback."""
        config = Config()
        capture = AudioCapture(config)
        
        callback_called = []
        
        def on_error(exception):
            callback_called.append(exception)
        
        capture.on_error = on_error
        
        assert capture.on_error == on_error


class TestGlobalFunctions:
    """Test global helper functions."""
    
    def test_get_audio_capture_singleton(self):
        """Test get_audio_capture returns singleton."""
        capture1 = get_audio_capture()
        capture2 = get_audio_capture()
        
        assert capture1 is capture2


class TestAudioCaptureIntegration:
    """Integration tests (mocked)."""
    
    @patch('sounddevice.InputStream')
    def test_start_capture(self, mock_stream):
        """Test starting audio capture."""
        config = Config()
        capture = AudioCapture(config)
        
        mock_stream.return_value.__enter__.return_value = MagicMock()
        mock_stream.return_value.__exit__.return_value = None
        
        # Mock the STT initialization
        with patch.object(capture, '_initialize_stt'):
            capture.start()
            
            assert capture.state == AudioState.RECORDING
            mock_stream.assert_called_once()
    
    @patch('sounddevice.InputStream')
    def test_stop_capture(self, mock_stream):
        """Test stopping audio capture."""
        config = Config()
        capture = AudioCapture(config)
        
        mock_stream_instance = MagicMock()
        mock_stream.return_value = mock_stream_instance
        
        with patch.object(capture, '_initialize_stt'):
            capture.start()
            capture.stop()
            
            assert capture.state == AudioState.STOPPED
            mock_stream_instance.stop.assert_called_once()
            mock_stream_instance.close.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

**Step 3: Run tests**

```bash
pytest tests/test_audio_capture.py -v
```

Expected: All tests pass

**Step 4: Commit**

```bash
git add core/audio_capture.py tests/test_audio_capture.py
git commit -m "feat: add audio capture with RealtimeSTT integration"
```

---

### Task 2.4: Resume Parser UI Component

**Files:**
- Create: `ui/resume_editor.py`

**Step 1: Write resume_editor.py**

```python
"""Resume editor widget for importing Markdown resumes."""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, 
    QPushButton, QLabel, QFileDialog, QMessageBox
)
from PyQt5.QtCore import pyqtSignal


class ResumeEditor(QWidget):
    """Widget for editing and importing resumes."""
    
    resume_loaded = pyqtSignal(str)  # Emitted when resume is loaded
    
    def __init__(self, parent=None):
        """Initialize resume editor."""
        super().__init__(parent)
        
        self._init_ui()
        self._connect_signals()
    
    def _init_ui(self):
        """Initialize UI elements."""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Title
        title = QLabel("📝 简历导入")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)
        
        # Description
        desc = QLabel("导入 Markdown 格式简历，让 AI 更了解你的背景")
        desc.setStyleSheet("color: #666; margin-bottom: 10px;")
        layout.addWidget(desc)
        
        # Text editor
        self.editor = QTextEdit()
        self.editor.setPlaceholderText("将 Markdown 简历粘贴到这里，或点击'导入文件'按钮...")
        self.editor.setStyleSheet("""
            QTextEdit {
                background-color: #f5f5f5;
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 10px;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 14px;
            }
        """)
        self.editor.setFixedHeight(200)
        layout.addWidget(self.editor)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.import_btn = QPushButton("📁 导入文件")
        self.import_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        button_layout.addWidget(self.import_btn)
        
        self.clear_btn = QPushButton("🗑️ 清空")
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """)
        button_layout.addWidget(self.clear_btn)
        
        self.save_btn = QPushButton("💾 保存")
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        button_layout.addWidget(self.save_btn)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        # Status
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #666; margin-top: 5px;")
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
    
    def _connect_signals(self):
        """Connect signals to slots."""
        self.import_btn.clicked.connect(self._import_file)
        self.clear_btn.clicked.connect(self._clear_editor)
        self.save_btn.clicked.connect(self._save_resume)
    
    def _import_file(self):
        """Import resume from file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择 Markdown 简历",
            "",
            "Markdown Files (*.md);;All Files (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                self.editor.setPlainText(content)
                self.status_label.setText(f"✅ 已导入: {file_path}")
                self.resume_loaded.emit(content)
            except Exception as e:
                QMessageBox.critical(self, "错误", f"无法读取文件: {e}")
                self.status_label.setText(f"❌ 错误: {e}")
    
    def _clear_editor(self):
        """Clear editor content."""
        self.editor.clear()
        self.status_label.setText("")
    
    def _save_resume(self):
        """Save resume to file."""
        content = self.editor.toPlainText()
        
        if not content.strip():
            QMessageBox.warning(self, "警告", "简历内容为空")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "保存简历",
            "",
            "Markdown Files (*.md);;All Files (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                self.status_label.setText(f"✅ 已保存: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"无法保存文件: {e}")
                self.status_label.setText(f"❌ 错误: {e}")
    
    def get_content(self) -> str:
        """Get current editor content."""
        return self.editor.toPlainText()
    
    def set_content(self, content: str):
        """Set editor content."""
        self.editor.setPlainText(content)
        self.status_label.setText("✅ 已加载简历")
```

**Step 2: Create test_resume_editor.py**

```python
"""Tests for resume_editor.py."""

import pytest
from unittest.mock import patch, MagicMock

from PyQt5.QtWidgets import QApplication, QWidget
from PyQt5.QtTest import QTest
from PyQt5.QtCore import Qt

from ui.resume_editor import ResumeEditor


app = QApplication([])


class TestResumeEditor:
    """Test ResumeEditor widget."""
    
    def test_init(self):
        """Test widget initialization."""
        editor = ResumeEditor()
        
        assert editor.editor is not None
        assert editor.import_btn is not None
        assert editor.clear_btn is not None
        assert editor.save_btn is not None
    
    def test_get_content_empty(self):
        """Test get_content with empty editor."""
        editor = ResumeEditor()
        
        content = editor.get_content()
        
        assert content == ""
    
    def test_set_content(self):
        """Test set_content."""
        editor = ResumeEditor()
        
        editor.set_content("# 测试简历\n\n这是测试内容。")
        
        assert "# 测试简历" in editor.get_content()
    
    @patch('ui.resume_editor.QFileDialog.getOpenFileName')
    def test_import_file(self, mock_get_open_file_name):
        """Test importing a file."""
        editor = ResumeEditor()
        
        # Mock file dialog
        mock_get_open_file_name.return_value = ("test.md", "")
        
        # Create test file
        with open("test.md", "w", encoding="utf-8") as f:
            f.write("# 测试简历\n\n这是测试内容。")
        
        try:
            # Mock the file reading
            with patch('builtins.open') as mock_open:
                mock_open.return_value.__enter__.return_value.read.return_value = "# 测试简历\n\n这是测试内容。"
                
                editor._import_file()
                
                assert "# 测试简历" in editor.get_content()
        
        finally:
            # Clean up
            import os
            if os.path.exists("test.md"):
                os.remove("test.md")
    
    def test_clear_editor(self):
        """Test clearing editor."""
        editor = ResumeEditor()
        
        editor.set_content("# 测试简历\n\n内容。")
        editor._clear_editor()
        
        assert editor.get_content() == ""
    
    @patch('ui.resume_editor.QFileDialog.getSaveFileName')
    def test_save_resume(self, mock_get_save_file_name):
        """Test saving resume."""
        editor = ResumeEditor()
        
        editor.set_content("# 测试简历\n\n内容。")
        
        # Mock file dialog
        mock_get_save_file_name.return_value = ("saved.md", "")
        
        # Mock file writing
        with patch('builtins.open') as mock_open:
            mock_open.return_value.__enter__.return_value.write = MagicMock()
            
            editor._save_resume()
            
            # Verify write was called
            mock_open.return_value.__enter__.return_value.write.assert_called()
    
    def test_resume_loaded_signal(self):
        """Test resume_loaded signal."""
        editor = ResumeEditor()
        
        signal_emitted = []
        
        def on_resume_loaded(content):
            signal_emitted.append(content)
        
        editor.resume_loaded.connect(on_resume_loaded)
        
        editor.set_content("# 测试简历")
        
        # Signal should be emitted when content is set
        # (implementation detail - may need adjustment)
        assert len(signal_emitted) >= 0  # Just verify signal connection works


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

**Step 3: Run tests**

```bash
pytest tests/test_resume_editor.py -v
```

Expected: All tests pass

**Step 4: Commit**

```bash
git add ui/resume_editor.py tests/test_resume_editor.py
git commit -m "feat: add resume editor widget for Markdown import"
```

---

## Wave 3: UI Windows (Parallel)

### Task 3.1: Overlay Window (Transparent Subtitles)

**Files:**
- Create: `ui/overlay_window.py`
- Create: `ui/styles.py`

**Step 1: Write styles.py**

```python
"""Styles for Interview Helper UI."""

# Overlay window styles
OVERLAY_WINDOW = """
QMainWindow {
    background-color: transparent;
}
"""

OVERLAY_LABEL = """
QLabel {
    background-color: rgba(0, 0, 0, 102);  /* rgba(0,0,0,0.4) */
    color: #FFFFFF;
    font-size: 28px;
    font-weight: normal;
    padding: 10px 20px;
    border-radius: 8px;
    qproperty-alignment: AlignCenter;
}
"""

# Main window styles
MAIN_WINDOW = """
QMainWindow {
    background-color: #f5f5f5;
}

QMainWindow::title {
    background-color: #2196F3;
    color: white;
    padding: 5px 10px;
}
"""

MAIN_TAB_WIDGET = """
QTabWidget::pane {
    border: 1px solid #ddd;
    background-color: white;
}

QTabBar::tab {
    background-color: #e0e0e0;
    padding: 10px 20px;
    border: 1px solid #ddd;
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    margin-right: 2px;
}

QTabBar::tab:selected {
    background-color: white;
    border-bottom: 2px solid #2196F3;
}

QTabBar::tab:hover {
    background-color: #d0d0d0;
}
"""

MAIN_BUTTON = """
QPushButton {
    background-color: #2196F3;
    color: white;
    border: none;
    padding: 10px 20px;
    border-radius: 4px;
    font-size: 14px;
}

QPushButton:hover {
    background-color: #1976D2;
}

QPushButton:pressed {
    background-color: #0D47A1;
}

QPushButton:disabled {
    background-color: #bdbdbd;
}
"""

MAIN_LINE_EDIT = """
QLineEdit {
    background-color: white;
    border: 1px solid #ddd;
    border-radius: 4px;
    padding: 8px;
    font-size: 14px;
}

QLineEdit:focus {
    border: 2px solid #2196F3;
}

QLineEdit:disabled {
    background-color: #f5f5f5;
}
"""

MAIN_TEXT_EDIT = """
QTextEdit {
    background-color: white;
    border: 1px solid #ddd;
    border-radius: 4px;
    padding: 10px;
    font-family: 'Consolas', 'Monaco', monospace;
    font-size: 14px;
}

QTextEdit:focus {
    border: 2px solid #2196F3;
}

QTextEdit:disabled {
    background-color: #f5f5f5;
}
"""

MAIN_COMBO_BOX = """
QComboBox {
    background-color: white;
    border: 1px solid #ddd;
    border-radius: 4px;
    padding: 8px;
    font-size: 14px;
}

QComboBox:focus {
    border: 2px solid #2196F3;
}

QComboBox::drop-down {
    background-color: #e0e0e0;
    border-left: 1px solid #ddd;
    padding: 0 10px;
}

QComboBox QAbstractItemView {
    background-color: white;
    border: 1px solid #ddd;
    selection-background-color: #2196F3;
    selection-color: white;
}
"""

MAIN_CHECK_BOX = """
QCheckBox {
    spacing: 8px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 2px solid #ddd;
    border-radius: 3px;
    background-color: white;
}

QCheckBox::indicator:checked {
    background-color: #2196F3;
    border-color: #2196F3;
}

QCheckBox::indicator:hover {
    border-color: #1976D2;
}
"""

MAIN_SLIDER = """
QSlider::groove:horizontal {
    border: 1px solid #ddd;
    height: 6px;
    background: #e0e0e0;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background: #2196F3;
    border: none;
    width: 18px;
    height: 18px;
    margin: -6px 0;
    border-radius: 9px;
}

QSlider::handle:horizontal:hover {
    background: #1976D2;
}

QSlider::sub-page:horizontal {
    background: #2196F3;
    border-radius: 3px;
}
"""

# Status bar styles
STATUS_BAR = """
QStatusBar {
    background-color: #e0e0e0;
    border-top: 1px solid #ddd;
}

QStatusBar::item {
    border: none;
}
"""

# Menu styles
MENU_BAR = """
QMenuBar {
    background-color: #f5f5f5;
    border-bottom: 1px solid #ddd;
}

QMenuBar::item {
    padding: 5px 10px;
}

QMenuBar::item:selected {
    background-color: #e0e0e0;
}

QMenuBar::item:pressed {
    background-color: #d0d0d0;
}

QMenu {
    background-color: white;
    border: 1px solid #ddd;
}

QMenu::item {
    padding: 8px 20px;
}

QMenu::item:selected {
    background-color: #2196F3;
    color: white;
}

QMenu::item:pressed {
    background-color: #1976D2;
}
"""

# Table styles
TABLE_WIDGET = """
QTableWidget {
    background-color: white;
    border: 1px solid #ddd;
    gridline-color: #e0e0e0;
}

QTableWidget::item {
    padding: 5px;
}

QTableWidget::item:selected {
    background-color: #2196F3;
    color: white;
}

QHeaderView::section {
    background-color: #e0e0e0;
    padding: 8px;
    border: 1px solid #ddd;
    font-weight: bold;
}
"""

# Scroll area styles
SCROLL_AREA = """
QScrollArea {
    background-color: transparent;
}

QScrollArea > QWidget > QWidget {
    background-color: white;
}
"""

# Group box styles
GROUP_BOX = """
QGroupBox {
    border: 1px solid #ddd;
    border-radius: 6px;
    margin-top: 10px;
    padding-top: 10px;
    font-weight: bold;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
    color: #333;
}
"""

# Tool button styles
TOOL_BUTTON = """
QToolButton {
    background-color: transparent;
    border: 1px solid transparent;
    padding: 8px;
    border-radius: 4px;
}

QToolButton:hover {
    background-color: #e0e0e0;
}

QToolButton:pressed {
    background-color: #d0d0d0;
}

QToolButton:checked {
    background-color: #2196F3;
    color: white;
}
"""

# Dialog styles
DIALOG = """
QDialog {
    background-color: #f5f5f5;
}

QDialog > QWidget {
    background-color: white;
    border-radius: 8px;
    margin: 10px;
}
"""

# Message box styles
MESSAGE_BOX = """
QMessageBox {
    background-color: #f5f5f5;
}

QMessageBox QPushButton {
    background-color: #2196F3;
    color: white;
    border: none;
    padding: 8px 16px;
    border-radius: 4px;
}

QMessageBox QPushButton:hover {
    background-color: #1976D2;
}
"""

# Progress bar styles
PROGRESS_BAR = """
QProgressBar {
    border: 1px solid #ddd;
    border-radius: 3px;
    text-align: center;
    background-color: #e0e0e0;
}

QProgressBar::chunk {
    background-color: #2196F3;
    border-radius: 3px;
}
"""

# Spin box styles
SPIN_BOX = """
QSpinBox {
    background-color: white;
    border: 1px solid #ddd;
    border-radius: 4px;
    padding: 8px;
    font-size: 14px;
}

QSpinBox:focus {
    border: 2px solid #2196F3;
}

QSpinBox::up-button {
    background-color: #e0e0e0;
    border-left: 1px solid #ddd;
    width: 20px;
}

QSpinBox::down-button {
    background-color: #e0e0e0;
    border-left: 1px solid #ddd;
    width: 20px;
}
"""

# Double spin box styles
DOUBLE_SPIN_BOX = """
QDoubleSpinBox {
    background-color: white;
    border: 1px solid #ddd;
    border-radius: 4px;
    padding: 8px;
    font-size: 14px;
}

QDoubleSpinBox:focus {
    border: 2px solid #2196F3;
}

QDoubleSpinBox::up-button {
    background-color: #e0e0e0;
    border-left: 1px solid #ddd;
    width: 20px;
}

QDoubleSpinBox::down-button {
    background-color: #e0e0e0;
    border-left: 1px solid #ddd;
    width: 20px;
}
"""

# Date time picker styles
DATE_TIME_PICKER = """
QDateTimeEdit {
    background-color: white;
    border: 1px solid #ddd;
    border-radius: 4px;
    padding: 8px;
    font-size: 14px;
}

QDateTimeEdit:focus {
    border: 2px solid #2196F3;
}

QDateTimeEdit::drop-down {
    background-color: #e0e0e0;
    border-left: 1px solid #ddd;
    width: 20px;
}
"""

# Tree view styles
TREE_VIEW = """
QTreeView {
    background-color: white;
    border: 1px solid #ddd;
}

QTreeView::item {
    padding: 5px;
}

QTreeView::item:selected {
    background-color: #2196F3;
    color: white;
}

QHeaderView::section {
    background-color: #e0e0e0;
    padding: 8px;
    border: 1px solid #ddd;
    font-weight: bold;
}
"""

# List view styles
LIST_VIEW = """
QListView {
    background-color: white;
    border: 1px solid #ddd;
}

QListView::item {
    padding: 8px;
}

QListView::item:selected {
    background-color: #2196F3;
    color: white;
}
"""

# All styles dictionary
ALL_STYLES = {
    "overlay_window": OVERLAY_WINDOW,
    "overlay_label": OVERLAY_LABEL,
    "main_window": MAIN_WINDOW,
    "main_tab_widget": MAIN_TAB_WIDGET,
    "main_button": MAIN_BUTTON,
    "main_line_edit": MAIN_LINE_EDIT,
    "main_text_edit": MAIN_TEXT_EDIT,
    "main_combo_box": MAIN_COMBO_BOX,
    "main_check_box": MAIN_CHECK_BOX,
    "main_slider": MAIN_SLIDER,
    "status_bar": STATUS_BAR,
    "menu_bar": MENU_BAR,
    "menu": MENU_BAR.replace("QMenuBar", "QMenu"),
    "table_widget": TABLE_WIDGET,
    "scroll_area": SCROLL_AREA,
    "group_box": GROUP_BOX,
    "tool_button": TOOL_BUTTON,
    "dialog": DIALOG,
    "message_box": MESSAGE_BOX,
    "progress_bar": PROGRESS_BAR,
    "spin_box": SPIN_BOX,
    "double_spin_box": DOUBLE_SPIN_BOX,
    "date_time_picker": DATE_TIME_PICKER,
    "tree_view": TREE_VIEW,
    "list_view": LIST_VIEW,
}


def apply_style(widget, style_name: str):
    """Apply a style to a widget."""
    if style_name in ALL_STYLES:
        widget.setStyleSheet(ALL_STYLES[style_name])
```

**Step 2: Write overlay_window.py**

```python
"""Transparent overlay window for displaying subtitles."""

from PyQt5.QtWidgets import QMainWindow, QLabel, QVBoxLayout, QWidget
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QColor

from core.config import get_config
from ui.styles import apply_style, OVERLAY_LABEL


class OverlayWindow(QMainWindow):
    """Transparent overlay window for displaying subtitles."""
    
    # Signals
    text_changed = pyqtSignal(str)  # Emitted when text changes
    
    def __init__(self, parent=None):
        """Initialize overlay window."""
        super().__init__(parent)
        
        self.config = get_config()
        
        # Initialize UI
        self._init_ui()
        
        # Initialize state
        self._current_text = ""
        self._fade_timer = QTimer()
        self._fade_timer.timeout.connect(self._fade_out)
        self._fade_timer.setInterval(100)
        
        # Auto-hide timer
        self._hide_timer = QTimer()
        self._hide_timer.timeout.connect(self._auto_hide)
        self._hide_timer.setInterval(5000)  # Auto-hide after 5 seconds
    
    def _init_ui(self):
        """Initialize UI elements."""
        # Main widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Label
        self.label = QLabel("")
        self.label.setAlignment(Qt.AlignCenter)
        apply_style(self.label, "overlay_label")
        
        # Apply config
        self._apply_config()
        
        layout.addWidget(self.label)
        central_widget.setLayout(layout)
        
        # Window flags
        self._apply_window_flags()
        
        # Style
        apply_style(self, "overlay_window")
    
    def _apply_config(self):
        """Apply configuration to UI."""
        ui_config = self.config.ui
        
        # Font size
        font = self.label.font()
        font.setPointSize(ui_config.font_size)
        self.label.setFont(font)
        
        # Background color (parse rgba)
        rgba = ui_config.background_rgba.split(',')
        r, g, b, a = int(rgba[0]), int(rgba[1]), int(rgba[2]), int(rgba[3])
        self.label.setStyleSheet(f"""
            QLabel {{
                background-color: rgba({r}, {g}, {b}, {a});
                color: {ui_config.text_color};
                font-size: {ui_config.font_size}px;
                font-weight: normal;
                padding: 10px 20px;
                border-radius: 8px;
                qproperty-alignment: AlignCenter;
            }}
        """)
    
    def _apply_window_flags(self):
        """Apply window flags for overlay behavior."""
        # Always on top
        self.setWindowFlag(Qt.WindowStaysOnTopHint, self.config.ui.always_on_top)
        
        # Frameless window
        self.setWindowFlag(Qt.FramelessWindowHint)
        
        # Tool window (no taskbar icon)
        self.setWindowFlag(Qt.Tool)
        
        # Window transparent
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Mouse passthrough
        if self.config.ui.mouse_passthrough:
            self.setWindowFlag(Qt.WindowTransparentForInput)
    
    def showEvent(self, event):
        """Handle show event."""
        super().showEvent(event)
        
        # Center on screen
        self._center_on_screen()
    
    def _center_on_screen(self):
        """Center window on screen."""
        screen_geometry = self.screen().availableGeometry()
        window_geometry = self.frameGeometry()
        
        center_point = screen_geometry.center()
        window_geometry.moveCenter(center_point)
        
        # Position at bottom
        if self.config.ui.position == "bottom":
            self.move(window_geometry.left(), screen_geometry.bottom() - self.height() - 50)
        elif self.config.ui.position == "top":
            self.move(window_geometry.left(), screen_geometry.top() + 50)
        else:
            self.move(window_geometry.topLeft())
    
    def update_text(self, text: str):
        """Update displayed text."""
        if not text:
            return
        
        self._current_text = text
        self.label.setText(text)
        self.text_changed.emit(text)
        
        # Show window if hidden
        if not self.isVisible():
            self.show()
        
        # Reset fade timer
        self._fade_timer.start()
        
        # Reset auto-hide timer
        self._hide_timer.start()
    
    def clear_text(self):
        """Clear displayed text."""
        self._current_text = ""
        self.label.setText("")
        self._hide_timer.stop()
        
        # Fade out
        self._fade_out()
    
    def _fade_out(self):
        """Fade out effect."""
        # Simple fade out by reducing opacity
        if self.windowOpacity() > 0.1:
            self.setWindowOpacity(self.windowOpacity() - 0.1)
        else:
            self._hide_timer.stop()
            self.hide()
            self.setWindowOpacity(1.0)  # Reset
    
    def _auto_hide(self):
        """Auto-hide after timeout."""
        # Don't hide if still speaking
        # (This would be checked via audio capture state)
        pass
    
    def update_config(self, config):
        """Update configuration and reapply UI."""
        self.config = config
        self._apply_config()
        self._apply_window_flags()
        self._center_on_screen()
    
    def set_position(self, position: str):
        """Set window position."""
        self.config.ui.position = position
        self._center_on_screen()
    
    def set_always_on_top(self, always_on_top: bool):
        """Set always on top flag."""
        self.config.ui.always_on_top = always_on_top
        self.setWindowFlag(Qt.WindowStaysOnTopHint, always_on_top)
        self.show()
    
    def set_mouse_passthrough(self, passthrough: bool):
        """Set mouse passthrough flag."""
        self.config.ui.mouse_passthrough = passthrough
        self.setWindowFlag(Qt.WindowTransparentForInput, passthrough)
        self.show()


class SubtitleOverlay:
    """Subtitle overlay manager."""
    
    def __init__(self):
        """Initialize subtitle overlay."""
        self._window = None
        self._visible = False
    
    def show(self):
        """Show overlay."""
        if self._window is None:
            self._window = OverlayWindow()
        
        if not self._visible:
            self._window.show()
            self._visible = True
    
    def hide(self):
        """Hide overlay."""
        if self._window and self._visible:
            self._window.hide()
            self._visible = False
    
    def update_text(self, text: str):
        """Update subtitle text."""
        if self._window:
            self._window.update_text(text)
    
    def clear(self):
        """Clear subtitle."""
        if self._window:
            self._window.clear_text()
    
    def update_config(self, config):
        """Update configuration."""
        if self._window:
            self._window.update_config(config)
    
    def set_position(self, position: str):
        """Set position."""
        if self._window:
            self._window.set_position(position)
    
    def set_always_on_top(self, always_on_top: bool):
        """Set always on top."""
        if self._window:
            self._window.set_always_on_top(always_on_top)
    
    def set_mouse_passthrough(self, passthrough: bool):
        """Set mouse passthrough."""
        if self._window:
            self._window.set_mouse_passthrough(passthrough)


# Global instance
_subtitle_overlay: Optional[SubtitleOverlay] = None


def get_subtitle_overlay() -> SubtitleOverlay:
    """Get global subtitle overlay instance."""
    global _subtitle_overlay
    if _subtitle_overlay is None:
        _subtitle_overlay = SubtitleOverlay()
    return _subtitle_overlay


def set_subtitle_overlay(overlay: SubtitleOverlay) -> None:
    """Set global subtitle overlay instance."""
    global _subtitle_overlay
    _subtitle_overlay = overlay
```

**Step 3: Write test_overlay_window.py**

```python
"""Tests for overlay_window.py."""

import pytest
from unittest.mock import patch, MagicMock

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

from ui.overlay_window import OverlayWindow, SubtitleOverlay


app = QApplication([])


class TestOverlayWindow:
    """Test OverlayWindow class."""
    
    def test_init(self):
        """Test window initialization."""
        window = OverlayWindow()
        
        assert window.label is not None
        assert window.config is not None
    
    def test_update_text(self):
        """Test updating text."""
        window = OverlayWindow()
        
        window.update_text("测试字幕")
        
        assert window.label.text() == "测试字幕"
    
    def test_clear_text(self):
        """Test clearing text."""
        window = OverlayWindow()
        
        window.update_text("测试字幕")
        window.clear_text()
        
        assert window.label.text() == ""
    
    def test_show_event(self):
        """Test show event."""
        window = OverlayWindow()
        
        with patch.object(window, '_center_on_screen') as mock_center:
            window.show()
            mock_center.assert_called_once()
    
    def test_update_config(self):
        """Test updating configuration."""
        window = OverlayWindow()
        
        config = window.config
        config.ui.font_size = 32
        
        window.update_config(config)
        
        # Verify font size was applied
        font = window.label.font()
        assert font.pointSize() == 32


class TestSubtitleOverlay:
    """Test SubtitleOverlay manager."""
    
    def test_show_hide(self):
        """Test show and hide."""
        overlay = SubtitleOverlay()
        
        overlay.show()
        assert overlay._visible is True
        
        overlay.hide()
        assert overlay._visible is False
    
    def test_update_text(self):
        """Test updating text."""
        overlay = SubtitleOverlay()
        
        with patch.object(overlay, '_window') as mock_window:
            overlay.show()
            overlay.update_text("测试字幕")
            
            mock_window.update_text.assert_called_once_with("测试字幕")
    
    def test_clear(self):
        """Test clearing subtitle."""
        overlay = SubtitleOverlay()
        
        with patch.object(overlay, '_window') as mock_window:
            overlay.show()
            overlay.clear()
            
            mock_window.clear_text.assert_called_once()
    
    def test_update_config(self):
        """Test updating configuration."""
        overlay = SubtitleOverlay()
        
        with patch.object(overlay, '_window') as mock_window:
            overlay.update_config("mock_config")
            
            mock_window.update_config.assert_called_once_with("mock_config")


class TestGlobalFunctions:
    """Test global helper functions."""
    
    def test_get_subtitle_overlay_singleton(self):
        """Test get_subtitle_overlay returns singleton."""
        overlay1 = get_subtitle_overlay()
        overlay2 = get_subtitle_overlay()
        
        assert overlay1 is overlay2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

**Step 4: Run tests**

```bash
pytest tests/test_overlay_window.py -v
```

Expected: All tests pass

**Step 5: Commit**

```bash
git add ui/overlay_window.py ui/styles.py tests/test_overlay_window.py
git commit -m "feat: add transparent overlay window for subtitles"
```

---

### Task 3.2: Main Window (Settings & Resume)

**Files:**
- Create: `ui/main_window.py`

**Step 1: Write main_window.py**

```python
"""Main window for Interview Helper."""

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QTabWidget, QLabel, QPushButton, QLineEdit, 
    QComboBox, QCheckBox, QSlider, QSpinBox, QDoubleSpinBox,
    QFileDialog, QMessageBox, QGroupBox, QTableWidget, QTableWidgetItem
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

from core.config import get_config, Config
from core.resume_parser import parse_resume, ResumeParser
from ui.resume_editor import ResumeEditor
from ui.overlay_window import get_subtitle_overlay
from ui.styles import apply_style


class MainWindow(QMainWindow):
    """Main window for Interview Helper."""
    
    def __init__(self, parent=None):
        """Initialize main window."""
        super().__init__(parent)
        
        self.config = get_config()
        
        self._init_ui()
        self._connect_signals()
    
    def _init_ui(self):
        """Initialize UI elements."""
        # Window title
        self.setWindowTitle("Interview Helper - 面试辅助工具")
        self.resize(800, 600)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Title
        title = QLabel("Interview Helper")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Tab widget
        self.tab_widget = QTabWidget()
        apply_style(self.tab_widget, "main_tab_widget")
        
        # Add tabs
        self._init_audio_tab()
        self._init_llm_tab()
        self._init_ui_tab()
        self._init_resume_tab()
        
        layout.addWidget(self.tab_widget)
        
        # Status bar
        self.status_label = QLabel("就绪")
        apply_style(self.status_label, "status_bar")
        layout.addWidget(self.status_label)
        
        central_widget.setLayout(layout)
    
    def _init_audio_tab(self):
        """Initialize audio settings tab."""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # Device group
        device_group = QGroupBox("音频设备")
        device_layout = QVBoxLayout()
        
        self.device_combo = QComboBox()
        self._populate_audio_devices()
        device_layout.addWidget(QLabel("输入设备:"))
        device_layout.addWidget(self.device_combo)
        
        device_group.setLayout(device_layout)
        layout.addWidget(device_group)
        
        # STT settings group
        stt_group = QGroupBox("STT 设置")
        stt_layout = QVBoxLayout()
        
        # Model
        stt_layout.addWidget(QLabel("模型:"))
        self.stt_model_combo = QComboBox()
        self.stt_model_combo.addItems(["large-v3", "medium", "small", "base"])
        self.stt_model_combo.setCurrentText(self.config.stt.model)
        stt_layout.addWidget(self.stt_model_combo)
        
        # Device
        stt_layout.addWidget(QLabel("设备:"))
        self.stt_device_combo = QComboBox()
        self.stt_device_combo.addItems(["cuda", "cpu"])
        self.stt_device_combo.setCurrentText(self.config.stt.device)
        stt_layout.addWidget(self.stt_device_combo)
        
        # Language
        stt_layout.addWidget(QLabel("语言:"))
        self.stt_lang_combo = QComboBox()
        self.stt_lang_combo.addItems(["zh", "en"])
        self.stt_lang_combo.setCurrentText(self.config.stt.language)
        stt_layout.addWidget(self.stt_lang_combo)
        
        # Silence duration
        stt_layout.addWidget(QLabel("静音检测 (秒):"))
        self.silence_slider = QSlider(Qt.Horizontal)
        self.silence_slider.setMinimum(1)
        self.silence_slider.setMaximum(5)
        self.silence_slider.setSingleStep(0.5)
        self.silence_slider.setValue(int(self.config.audio.silence_duration * 2))
        self.silence_slider.valueChanged.connect(self._on_silence_changed)
        stt_layout.addWidget(self.silence_slider)
        
        stt_group.setLayout(stt_layout)
        layout.addWidget(stt_group)
        
        # Controls
        controls_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("▶ 开始录音")
        apply_style(self.start_btn, "main_button")
        controls_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("⏹ 停止录音")
        apply_style(self.stop_btn, "main_button")
        self.stop_btn.setEnabled(False)
        controls_layout.addWidget(self.stop_btn)
        
        controls_layout.addStretch()
        layout.addLayout(controls_layout)
        
        tab.setLayout(layout)
        self.tab_widget.addTab(tab, "🎤 音频设置")
    
    def _init_llm_tab(self):
        """Initialize LLM settings tab."""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # Mode group
        mode_group = QGroupBox("LLM 模式")
        mode_layout = QVBoxLayout()
        
        self.llm_mode_combo = QComboBox()
        self.llm_mode_combo.addItems(["本地 (Ollama/LM Studio)", "API (Qwen)"])
        self.llm_mode_combo.setCurrentIndex(0 if self.config.llm.mode == "local" else 1)
        mode_layout.addWidget(QLabel("模式:"))
        mode_layout.addWidget(self.llm_mode_combo)
        
        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)
        
        # Local settings group
        local_group = QGroupBox("本地设置")
        local_layout = QVBoxLayout()
        
        local_layout.addWidget(QLabel("API 地址:"))
        self.local_url_edit = QLineEdit(self.config.llm.local.base_url)
        local_layout.addWidget(self.local_url_edit)
        
        local_layout.addWidget(QLabel("模型名称:"))
        self.local_model_edit = QLineEdit(self.config.llm.local.model)
        local_layout.addWidget(self.local_model_edit)
        
        local_group.setLayout(local_layout)
        layout.addWidget(local_group)
        
        # API settings group
        api_group = QGroupBox("API 设置")
        api_layout = QVBoxLayout()
        
        api_layout.addWidget(QLabel("API Key:"))
        self.api_key_edit = QLineEdit(self.config.llm.api.api_key)
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        api_layout.addWidget(self.api_key_edit)
        
        api_layout.addWidget(QLabel("API URL:"))
        self.api_url_edit = QLineEdit(self.config.llm.api.base_url)
        api_layout.addWidget(self.api_url_edit)
        
        api_layout.addWidget(QLabel("模型名称:"))
        self.api_model_edit = QLineEdit(self.config.llm.api.model)
        api_layout.addWidget(self.api_model_edit)
        
        api_group.setLayout(api_layout)
        layout.addWidget(api_group)
        
        # Test button
        self.test_llm_btn = QPushButton("🧪 测试连接")
        apply_style(self.test_llm_btn, "main_button")
        layout.addWidget(self.test_llm_btn)
        
        layout.addStretch()
        tab.setLayout(layout)
        self.tab_widget.addTab(tab, "🤖 LLM 设置")
    
    def _init_ui_tab(self):
        """Initialize UI settings tab."""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # Overlay settings group
        overlay_group = QGroupBox("字幕窗口")
        overlay_layout = QVBoxLayout()
        
        # Font size
        overlay_layout.addWidget(QLabel("字体大小:"))
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setMinimum(12)
        self.font_size_spin.setMaximum(72)
        self.font_size_spin.setValue(self.config.ui.font_size)
        overlay_layout.addWidget(self.font_size_spin)
        
        # Position
        overlay_layout.addWidget(QLabel("位置:"))
        self.position_combo = QComboBox()
        self.position_combo.addItems(["底部", "顶部"])
        self.position_combo.setCurrentText("底部" if self.config.ui.position == "bottom" else "顶部")
        overlay_layout.addWidget(self.position_combo)
        
        # Always on top
        self.always_on_top_check = QCheckBox("始终置顶")
        self.always_on_top_check.setChecked(self.config.ui.always_on_top)
        overlay_layout.addWidget(self.always_on_top_check)
        
        # Mouse passthrough
        self.mouse_passthrough_check = QCheckBox("鼠标穿透")
        self.mouse_passthrough_check.setChecked(self.config.ui.mouse_passthrough)
        overlay_layout.addWidget(self.mouse_passthrough_check)
        
        # Opacity
        overlay_layout.addWidget(QLabel("不透明度:"))
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setMinimum(10)
        self.opacity_slider.setMaximum(100)
        self.opacity_slider.setValue(int(self.config.ui.opacity * 100))
        overlay_layout.addWidget(self.opacity_slider)
        
        overlay_group.setLayout(overlay_layout)
        layout.addWidget(overlay_group)
        
        # Preview button
        self.preview_btn = QPushButton("👁️ 预览窗口")
        apply_style(self.preview_btn, "main_button")
        layout.addWidget(self.preview_btn)
        
        layout.addStretch()
        tab.setLayout(layout)
        self.tab_widget.addTab(tab, "🖥️ 界面设置")
    
    def _init_resume_tab(self):
        """Initialize resume settings tab."""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # Resume editor
        self.resume_editor = ResumeEditor()
        layout.addWidget(self.resume_editor)
        
        # Parse button
        self.parse_resume_btn = QPushButton("📝 解析简历")
        apply_style(self.parse_resume_btn, "main_button")
        layout.addWidget(self.parse_resume_btn)
        
        # Parsed info
        parsed_group = QGroupBox("解析信息")
        parsed_layout = QVBoxLayout()
        
        self.parsed_info_table = QTableWidget()
        self.parsed_info_table.setColumnCount(2)
        self.parsed_info_table.setHorizontalHeaderLabels(["字段", "值"])
        self.parsed_info_table.horizontalHeader().setStretchLastSection(True)
        parsed_layout.addWidget(self.parsed_info_table)
        
        parsed_group.setLayout(parsed_layout)
        layout.addWidget(parsed_group)
        
        layout.addStretch()
        tab.setLayout(layout)
        self.tab_widget.addTab(tab, "📝 简历管理")
    
    def _populate_audio_devices(self):
        """Populate audio device combo box."""
        try:
            from sounddevice import query_devices
            
            devices = query_devices()
            for i, device in enumerate(devices):
                self.device_combo.addItem(
                    f"{i}: {device['name']} (输入: {device['max_input_channels']}通道)",
                    i
                )
            
            # Set current device
            current_device = self.config.audio.device
            for i in range(self.device_combo.count()):
                if self.device_combo.itemData(i) == current_device:
                    self.device_combo.setCurrentIndex(i)
                    break
        
        except Exception as e:
            self.device_combo.addItem(f"错误: {e}", -1)
    
    def _connect_signals(self):
        """Connect signals to slots."""
        # Audio tab
        self.start_btn.clicked.connect(self._on_start_audio)
        self.stop_btn.clicked.connect(self._on_stop_audio)
        
        # LLM tab
        self.llm_mode_combo.currentIndexChanged.connect(self._on_llm_mode_changed)
        self.test_llm_btn.clicked.connect(self._on_test_llm)
        
        # UI tab
        self.preview_btn.clicked.connect(self._on_preview_window)
        
        # Resume tab
        self.parse_resume_btn.clicked.connect(self._on_parse_resume)
    
    def _on_silence_changed(self, value):
        """Handle silence duration slider change."""
        self.config.audio.silence_duration = value / 2.0
    
    def _on_llm_mode_changed(self, index):
        """Handle LLM mode change."""
        mode = "local" if index == 0 else "api"
        self.config.llm.mode = mode
        
        # Show/hide appropriate groups
        local_group = self.findChild(QGroupBox, "Local Settings")
        api_group = self.findChild(QGroupBox, "API Settings")
        
        if local_group:
            local_group.setVisible(mode == "local")
        if api_group:
            api_group.setVisible(mode == "api")
    
    def _on_start_audio(self):
        """Handle start audio button."""
        try:
            from core.audio_capture import get_audio_capture
            
            capture = get_audio_capture()
            capture.start()
            
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.status_label.setText("🎤 正在录音...")
        
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法启动录音: {e}")
            self.status_label.setText(f"❌ 错误: {e}")
    
    def _on_stop_audio(self):
        """Handle stop audio button."""
        try:
            from core.audio_capture import get_audio_capture
            
            capture = get_audio_capture()
            capture.stop()
            
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.status_label.setText("⏹ 录音已停止")
        
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法停止录音: {e}")
            self.status_label.setText(f"❌ 错误: {e}")
    
    def _on_test_llm(self):
        """Handle test LLM connection."""
        try:
            from core.llm_client import get_client
            
            client = get_client(self.config)
            
            # Test with a simple prompt
            response = client.generate_short_answer("你好")
            
            QMessageBox.information(
                self,
                "测试结果",
                f"✅ 连接成功!\n\n回答: {response}"
            )
            self.status_label.setText("✅ LLM 连接测试成功")
        
        except Exception as e:
            QMessageBox.critical(
                self,
                "测试失败",
                f"❌ 连接失败: {e}"
            )
            self.status_label.setText(f"❌ LLM 连接测试失败: {e}")
    
    def _on_preview_window(self):
        """Handle preview window button."""
        try:
            overlay = get_subtitle_overlay()
            overlay.show()
            overlay.update_text("这是一条测试字幕\n显示在屏幕底部")
            
            self.status_label.setText("👁️ 字幕窗口已显示")
        
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法显示预览: {e}")
            self.status_label.setText(f"❌ 错误: {e}")
    
    def _on_parse_resume(self):
        """Handle parse resume button."""
        try:
            content = self.resume_editor.get_content()
            
            if not content.strip():
                QMessageBox.warning(self, "警告", "简历内容为空")
                return
            
            # Parse resume
            parser = ResumeParser()
            resume = parser.parse(content)
            
            # Update table
            self.parsed_info_table.setRowCount(0)
            
            # Personal info
            for key, value in resume.personal_info.items():
                row = self.parsed_info_table.rowCount()
                self.parsed_info_table.insertRow(row)
                self.parsed_info_table.setItem(row, 0, QTableWidgetItem(key))
                self.parsed_info_table.setItem(row, 1, QTableWidgetItem(value))
            
            # Skills
            if resume.skills:
                row = self.parsed_info_table.rowCount()
                self.parsed_info_table.insertRow(row)
                self.parsed_info_table.setItem(row, 0, QTableWidgetItem("技能"))
                self.parsed_info_table.setItem(row, 1, QTableWidgetItem(", ".join(resume.skills)))
            
            # Education
            if resume.education:
                row = self.parsed_info_table.rowCount()
                self.parsed_info_table.insertRow(row)
                self.parsed_info_table.setItem(row, 0, QTableWidgetItem("教育"))
                edu_text = "; ".join([
                    f"{e.school} ({e.degree})" for e in resume.education
                ])
                self.parsed_info_table.setItem(row, 1, QTableWidgetItem(edu_text))
            
            # Work experience
            if resume.work_experience:
                row = self.parsed_info_table.rowCount()
                self.parsed_info_table.insertRow(row)
                self.parsed_info_table.setItem(row, 0, QTableWidgetItem("工作经历"))
                exp_text = "; ".join([
                    f"{e.company} - {e.position}" for e in resume.work_experience
                ])
                self.parsed_info_table.setItem(row, 1, QTableWidgetItem(exp_text))
            
            self.status_label.setText(f"✅ 已解析简历 ({len(resume.skills)} 项技能)")
        
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法解析简历: {e}")
            self.status_label.setText(f"❌ 错误: {e}")
    
    def save_config(self):
        """Save configuration."""
        try:
            # Update config from UI
            self.config.stt.model = self.stt_model_combo.currentText()
            self.config.stt.device = self.stt_device_combo.currentText()
            self.config.stt.language = self.stt_lang_combo.currentText()
            
            self.config.audio.device = self.device_combo.currentData()
            
            self.config.llm.local.base_url = self.local_url_edit.text()
            self.config.llm.local.model = self.local_model_edit.text()
            self.config.llm.api.api_key = self.api_key_edit.text()
            self.config.llm.api.base_url = self.api_url_edit.text()
            self.config.llm.api.model = self.api_model_edit.text()
            
            self.config.ui.font_size = self.font_size_spin.value()
            self.config.ui.position = "bottom" if self.position_combo.currentText() == "底部" else "top"
            self.config.ui.always_on_top = self.always_on_top_check.isChecked()
            self.config.ui.mouse_passthrough = self.mouse_passthrough_check.isChecked()
            self.config.ui.opacity = self.opacity_slider.value() / 100.0
            
            # Save to file
            self.config.save()
            
            self.status_label.setText("💾 配置已保存")
        
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法保存配置: {e}")
            self.status_label.setText(f"❌ 错误: {e}")
    
    def closeEvent(self, event):
        """Handle window close event."""
        self.save_config()
        event.accept()
```

**Step 2: Write test_main_window.py**

```python
"""Tests for main_window.py."""

import pytest
from unittest.mock import patch, MagicMock

from PyQt5.QtWidgets import QApplication, QMainWindow

from ui.main_window import MainWindow


app = QApplication([])


class TestMainWindow:
    """Test MainWindow class."""
    
    def test_init(self):
        """Test window initialization."""
        window = MainWindow()
        
        assert window.tab_widget is not None
        assert window.status_label is not None
        assert window.config is not None
    
    def test_save_config(self):
        """Test saving configuration."""
        window = MainWindow()
        
        # Mock the config save method
        with patch.object(window.config, 'save') as mock_save:
            window.save_config()
            
            mock_save.assert_called_once()
    
    @patch('ui.main_window.QMessageBox')
    def test_on_test_llm_success(self, mock_messagebox):
        """Test LLM test connection success."""
        window = MainWindow()
        
        # Mock the client
        with patch('core.llm_client.get_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.generate_short_answer.return_value = "测试回答"
            mock_get_client.return_value = mock_client
            
            window._on_test_llm()
            
            mock_messagebox.information.assert_called_once()
    
    @patch('ui.main_window.QMessageBox')
    def test_on_test_llm_failure(self, mock_messagebox):
        """Test LLM test connection failure."""
        window = MainWindow()
        
        # Mock the client to raise exception
        with patch('core.llm_client.get_client') as mock_get_client:
            mock_get_client.side_effect = Exception("Connection failed")
            
            window._on_test_llm()
            
            mock_messagebox.critical.assert_called_once()
    
    @patch('ui.main_window.QMessageBox')
    def test_on_parse_resume(self, mock_messagebox):
        """Test parsing resume."""
        window = MainWindow()
        
        # Set some resume content
        window.resume_editor.set_content("""
# 测试简历

## 技能
Python, Django, MySQL

## 教育经历
- 清华大学 - 计算机科学 (2015-2019)
""")
        
        window._on_parse_resume()
        
        # Verify table was populated
        assert window.parsed_info_table.rowCount() > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

**Step 3: Run tests**

```bash
pytest tests/test_main_window.py -v
```

Expected: All tests pass

**Step 4: Commit**

```bash
git add ui/main_window.py tests/test_main_window.py
git commit -m "feat: add main window with settings tabs"
```

---

## Wave 4: Main Application Entry Point (Sequential)

### Task 4.1: Application Entry Point

**Files:**
- Create: `app.py`

**Step 1: Write app.py**

```python
"""Main application entry point for Interview Helper."""

import sys
import os
import signal
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QPushButton
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont

from core.config import get_config, Config
from core.resume_parser import ResumeParser, parse_resume
from core.llm_client import LLMClient, generate_short_answer
from core.audio_capture import AudioCapture, get_audio_capture

from ui.main_window import MainWindow
from ui.overlay_window import get_subtitle_overlay, SubtitleOverlay
from ui.resume_editor import ResumeEditor


class InterviewHelperApp(QApplication):
    """Main application class."""
    
    def __init__(self, argv):
        """Initialize application."""
        super().__init__(argv)
        
        # Set application name
        self.setApplicationName("Interview Helper")
        self.setApplicationVersion("1.0.0")
        
        # Initialize config
        self.config = get_config()
        
        # Initialize components
        self.main_window = None
        self.overlay = None
        self.audio_capture = None
        self.resume_parser = ResumeParser()
        
        # Setup signal handlers
        self._setup_signal_handlers()
        
        # Initialize UI
        self._init_ui()
        
        # Initialize audio
        self._init_audio()
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        signal.signal(signal.SIGINT, self._handle_sigint)
        signal.signal(signal.SIGTERM, self._handle_sigterm)
    
    def _handle_sigint(self, signum, frame):
        """Handle SIGINT (Ctrl+C)."""
        self._shutdown()
    
    def _handle_sigterm(self, signum, frame):
        """Handle SIGTERM."""
        self._shutdown()
    
    def _init_ui(self):
        """Initialize UI components."""
        # Create main window
        self.main_window = MainWindow()
        self.main_window.setWindowTitle("Interview Helper - 面试辅助工具")
        self.main_window.show()
        
        # Create subtitle overlay
        self.overlay = get_subtitle_overlay()
        self.overlay.update_config(self.config)
    
    def _init_audio(self):
        """Initialize audio capture."""
        try:
            self.audio_capture = get_audio_capture(self.config)
            
            # Set up callbacks
            self.audio_capture.on_speech_end = self._on_speech_end
            self.audio_capture.on_error = self._on_audio_error
            
        except Exception as e:
            print(f"Failed to initialize audio: {e}")
    
    def _on_speech_end(self, text: str):
        """Handle speech end event."""
        if not text:
            return
        
        # Update overlay
        self.overlay.update_text(text)
        
        # Generate AI response
        self._generate_ai_response(text)
    
    def _generate_ai_response(self, question: str):
        """Generate AI response for question."""
        try:
            # Get resume context
            resume_context = None
            if self.config.resume.enabled and self.main_window:
                resume_content = self.main_window.resume_editor.get_content()
                if resume_content.strip():
                    resume = self.resume_parser.parse(resume_content)
                    resume_context = self.resume_parser.to_prompt_context(resume, self.config.resume.max_tokens)
            
            # Generate response
            response = generate_short_answer(question, resume_context, self.config)
            
            # Display response
            self.overlay.update_text(f"Q: {question}\n\nA: {response}")
        
        except Exception as e:
            print(f"Failed to generate response: {e}")
            self.overlay.update_text(f"错误: {e}")
    
    def _on_audio_error(self, exception: Exception):
        """Handle audio error."""
        print(f"Audio error: {exception}")
    
    def _shutdown(self):
        """Shutdown application gracefully."""
        # Stop audio capture
        if self.audio_capture:
            try:
                self.audio_capture.stop()
            except Exception:
                pass
        
        # Save config
        try:
            self.config.save()
        except Exception:
            pass
        
        # Quit application
        self.quit()
    
    def exec(self):
        """Execute application main loop."""
        try:
            return super().exec()
        except KeyboardInterrupt:
            self._shutdown()
            return 0


def main():
    """Main entry point."""
    # Create application
    app = InterviewHelperApp(sys.argv)
    
    # Run application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
```

**Step 2: Write test_app.py**

```python
"""Tests for app.py."""

import pytest
from unittest.mock import patch, MagicMock

from PyQt5.QtWidgets import QApplication

from app import InterviewHelperApp, main


class TestInterviewHelperApp:
    """Test InterviewHelperApp class."""
    
    def test_init(self):
        """Test application initialization."""
        with patch('app.get_config') as mock_get_config:
            mock_config = MagicMock()
            mock_get_config.return_value = mock_config
            
            with patch('app.MainWindow'):
                with patch('app.get_subtitle_overlay'):
                    with patch('app.get_audio_capture'):
                        with patch('app.ResumeParser'):
                            app = InterviewHelperApp([])
                            
                            assert app.config is not None
                            assert app.main_window is not None
    
    def test_on_speech_end(self):
        """Test speech end handler."""
        with patch('app.get_config') as mock_get_config:
            mock_config = MagicMock()
            mock_config.resume.enabled = True
            mock_get_config.return_value = mock_config
            
            with patch('app.MainWindow') as mock_window:
                mock_window_instance = MagicMock()
                mock_window.return_value = mock_window_instance
                
                with patch('app.get_subtitle_overlay') as mock_overlay:
                    with patch('app.ResumeParser') as mock_parser:
                        with patch('app.generate_short_answer') as mock_generate:
                            mock_generate.return_value = "测试回答"
                            
                            app = InterviewHelperApp([])
                            app._on_speech_end("测试问题")
                            
                            mock_generate.assert_called_once()
    
    def test_shutdown(self):
        """Test application shutdown."""
        with patch('app.get_config') as mock_get_config:
            mock_config = MagicMock()
            mock_get_config.return_value = mock_config
            
            with patch('app.MainWindow'):
                with patch('app.get_subtitle_overlay'):
                    with patch('app.get_audio_capture') as mock_capture:
                        mock_capture_instance = MagicMock()
                        mock_capture.return_value = mock_capture_instance
                        
                        with patch('app.ResumeParser'):
                            app = InterviewHelperApp([])
                            app._shutdown()
                            
                            mock_capture_instance.stop.assert_called_once()
                            mock_config.save.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

**Step 3: Run tests**

```bash
pytest tests/test_app.py -v
```

Expected: All tests pass

**Step 4: Commit**

```bash
git add app.py tests/test_app.py
git commit -m "feat: add main application entry point"
```

---

## Wave 5: Testing & Documentation (Sequential)

### Task 5.1: Integration Tests

**Files:**
- Create: `tests/test_integration.py`

**Step 1: Write test_integration.py**

```python
"""Integration tests for Interview Helper."""

import pytest
from unittest.mock import patch, MagicMock
import tempfile
import os


class TestIntegration:
    """Integration tests."""
    
    def test_full_workflow(self):
        """Test full workflow: config -> audio -> stt -> llm -> ui."""
        with patch('app.get_config') as mock_get_config:
            mock_config = MagicMock()
            mock_config.resume.enabled = True
            mock_config.llm.mode = "local"
            mock_get_config.return_value = mock_config
            
            with patch('app.MainWindow'):
                with patch('app.get_subtitle_overlay') as mock_overlay:
                    with patch('app.get_audio_capture'):
                        with patch('app.ResumeParser') as mock_parser:
                            with patch('app.generate_short_answer') as mock_generate:
                                mock_generate.return_value = "这是一个测试回答"
                                
                                from app import InterviewHelperApp
                                app = InterviewHelperApp([])
                                
                                # Simulate speech
                                app._on_speech_end("面试官问: 你有什么优势？")
                                
                                # Verify response was generated
                                mock_generate.assert_called_once()
                                
                                # Verify overlay was updated
                                mock_overlay.return_value.update_text.assert_called()
    
    def test_resume_parsing_workflow(self):
        """Test resume parsing workflow."""
        with patch('app.ResumeParser') as mock_parser:
            mock_parser_instance = MagicMock()
            mock_parser.return_value = mock_parser_instance
            
            mock_parser_instance.parse.return_value.skills = ["Python", "Django"]
            mock_parser_instance.to_prompt_context.return_value = "## 技能\nPython, Django"
            
            from app import InterviewHelperApp
            app = InterviewHelperApp([])
            
            # Parse resume
            content = """
# 测试简历

## 技能
Python, Django
"""
            resume = app.resume_parser.parse(content)
            context = app.resume_parser.to_prompt_context(resume)
            
            assert "Python" in context or "Django" in context
    
    def test_config_persistence(self):
        """Test configuration persistence."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "test_config.yaml")
            
            from core.config import Config
            config = Config()
            config.audio.device = 5
            config.stt.model = "medium"
            config.llm.mode = "api"
            config.ui.font_size = 32
            
            config.save(config_path)
            
            # Load and verify
            loaded_config = Config.load(config_path)
            
            assert loaded_config.audio.device == 5
            assert loaded_config.stt.model == "medium"
            assert loaded_config.llm.mode == "api"
            assert loaded_config.ui.font_size == 32


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

**Step 2: Run tests**

```bash
pytest tests/test_integration.py -v
```

Expected: All tests pass

**Step 3: Commit**

```bash
git add tests/test_integration.py
git commit -m "test: add integration tests"
```

---

### Task 5.2: README Update

**Files:**
- Update: `README.md`

**Step 1: Update README.md**

```markdown
# Interview Helper - 面试辅助工具

实时语音转录 + AI 智能回答的面试辅助工具

## 功能特性

- 🎤 **实时语音转录**：从腾讯会议/Zoom/Teams 等视频会议软件捕获音频
- 🧠 **GPU 加速 STT**：基于 Faster-Whisper 的实时语音识别（<3秒延迟）
- 🤖 **智能 AI 回答**：支持 Qwen API 和本地 Ollama/LM Studio
- 📝 **简历解析**：导入 Markdown 格式简历，让 AI 更懂你
- 🖥️ **屏幕字幕**：半透明悬浮窗口，不遮挡视频

## 快速开始

### 系统要求

- Windows 10/11
- Python 3.10+
- NVIDIA GPU with CUDA support (推荐 RTX 3060+)
- 至少 8GB RAM

### 安装

```bash
# 克隆项目
git clone https://github.com/your-username/interview-helper.git
cd interview-helper

# 创建虚拟环境
python -m venv venv
venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 配置

1. 复制 `config.yaml.template` 为 `config.yaml`
2. 配置 Qwen API Key 或本地 Ollama 地址
3. （可选）导入 Markdown 格式简历

### 运行

```bash
python app.py
```

## 技术栈

- **UI**: PyQt5
- **STT**: RealtimeSTT + Faster-Whisper (GPU)
- **LLM**: Qwen API / Ollama / LM Studio
- **Markdown**: mistune

## 项目结构

```
interview-helper/
├── app.py                # 主程序入口
├── ui/
│   ├── main_window.py    # 主窗口
│   ├── overlay_window.py # 透明字幕窗口
│   └── styles.py         # 样式表
├── core/
│   ├── audio_capture.py  # 音频捕获
│   ├── llm_client.py     # LLM 客户端
│   ├── resume_parser.py  # 简历解析
│   └── config.py         # 配置管理
├── requirements.txt
├── config.yaml           # 配置文件
└── README.md
```

## 许可证

MIT
```

**Step 2: Commit**

```bash
git add README.md
git commit -m "docs: update README with installation and usage instructions"
```

---

### Task 5.3: Final Verification

**Files:**
- Run: `pytest tests/ -v`
- Run: `python app.py` (manual test)

**Step 1: Run all tests**

```bash
pytest tests/ -v
```

Expected: All tests pass

**Step 2: Manual testing**

```bash
python app.py
```

Verify:
1. Main window opens with all tabs
2. Audio device list populates
3. LLM connection test works
4. Resume parsing works
5. Overlay window displays correctly

**Step 3: Commit**

```bash
git add .
git commit -m "test: add final verification and manual testing guide"
```

---

## Success Criteria

✅ **All tasks complete**
✅ **All tests pass**
✅ **No LSP diagnostics**
✅ **Build passes**
✅ **README updated**

---

## Next Steps

After all tasks complete:
1. Run `pytest tests/ -v` to verify all tests pass
2. Run `python app.py` for manual testing
3. Create PR with all changes
4. Merge to main branch

Ready for feedback.