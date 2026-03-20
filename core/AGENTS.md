# CORE MODULE

## OVERVIEW

Business logic layer: audio capture (WASAPI loopback), Faster-Whisper STT, multi-provider LLM client, configuration singleton, resume parser.

## STRUCTURE

```
core/
├── __init__.py           # Package exports: Config, get_config, ResumeParser, LLMClient, AudioCapture
├── config.py             # Singleton Config with dot-notation access (916 lines)
├── audio_capture.py      # QThread audio capture + STT with PyQt signals (460 lines)
├── llm_client.py         # Multi-provider LLM: OpenAI/Ollama/LM Studio (378 lines)
├── llm_client_v2.py      # Alternative LLM client implementation
├── resume_parser.py      # Markdown resume → knowledge injection (246 lines)
├── logger.py             # Domain-specific loggers: stt, llm, system
└── stt_online.py         # Online STT service integration
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Config singleton | `config.py` | `get_config()` returns cached instance |
| Audio capture thread | `audio_capture.py` | WASAPI loopback + speech detection |
| LLM provider switching | `llm_client.py` | `switch_llm_from_file()` runtime change |
| Resume parsing | `resume_parser.py` | Regex-based section extraction |
| Logging | `logger.py` | `log_stt()`, `log_llm()`, `log_system()` |

## CONVENTIONS

### Module Exports
```python
# core/__init__.py
from .config import Config, get_config
from .resume_parser import ResumeParser
from .llm_client import LLMClient
from .audio_capture import AudioCapture
```

### Config Access Patterns
```python
# Dot-notation
config.get("llm.provider.openai.api_key")

# Property accessors
config.llm_mode
config.stt_model
config.input_device_index
```

### Signal Emissions (AudioCapture)
```python
transcription_ready.emit(text)
real_time_update.emit(partial_text)
recording_started.emit()
volume_update.emit(level)
```

### Logger Usage
```python
from core.logger import log_stt, log_llm, log_system

log_stt("Transcribed:", text)
log_llm("Generated:", response)
log_system("Event:", detail)
```

## ANTI-PATTERNS (THIS MODULE)

| Pattern | Location | Issue |
|---------|----------|-------|
| `global _config` | `config.py:212` | Global mutable state — limits testability |
| Type errors | `llm_client.py:32` | `str | None` returned where `str` expected |
| Multiple client versions | `llm_client.py` + `llm_client_v2.py` | Unclear which is canonical |

## NOTES

- **Config singleton**: Module-level `_config` variable, initialized once via `get_config()`
- **Cross-thread signals**: `AudioCapture` runs in QThread, emits PyQt signals to UI
- **Provider abstraction**: `llm.provider.{openai,ollama,lmstudio}` share same key structure
- **Resume injection**: Parsed resume injected into LLM prompt as knowledge context
