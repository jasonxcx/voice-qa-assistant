# PROJECT KNOWLEDGE BASE

**Generated:** 2026-03-20
**Branch:** feature/interview-helper

## OVERVIEW

Python desktop interview assistant — PyQt5 GUI with real-time STT (Faster-Whisper) and multi-provider LLM (Qwen/Ollama/LM Studio). Captures system audio, transcribes speech, generates answers, displays transparent overlay captions.

## STRUCTURE

```
interviewHelper/
├── app.py                    # Entry point: async event loop + module bootstrap
├── start.bat                 # Windows launcher: config check + deps + run
├── config.yaml               # Runtime config (gitignored, copy from template)
├── config.yaml.template      # Config template with documentation
├── requirements.txt          # Python dependencies
├── core/                     # Business logic: audio, STT, LLM, config
├── ui/                       # PyQt5 windows: main + transparent overlay
├── test/                     # Manual diagnostic scripts (not formal tests)
├── docs/plans/               # Dated design documents (YYYY-MM-DD-*.md)
├── debug_audio/              # Debug WAV files (gitignored)
└── logs/                     # Runtime logs: stt.log, llm.log, system.log
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Run application | `app.py` or `start.bat` | `start.bat` auto-checks config/deps |
| Configure LLM/STT | `config.yaml` | Copy from `config.yaml.template` |
| Audio capture logic | `core/audio_capture.py` | WASAPI loopback + Faster-Whisper |
| LLM client abstraction | `core/llm_client.py` | OpenAI/Ollama/LM Studio providers |
| Resume parsing | `core/resume_parser.py` | Markdown resume → knowledge injection |
| Main UI window | `ui/main_window.py` | 916 lines: config sync, device selection |
| Overlay captions | `ui/overlay_window.py` | 728 lines: drag/resize, F12 hotkey |
| Shared styles | `ui/styles.py` | Dark theme, status colors |

## CODE MAP

| Symbol | Type | Location | Role |
|--------|------|----------|------|
| `main()` | Function | `app.py:38` | Application bootstrap: creates QApplication, modules, event loop |
| `Config` | Class | `core/config.py` | Singleton configuration with dot-notation access |
| `get_config()` | Function | `core/config.py:212` | Returns cached Config singleton |
| `AudioCapture` | Class | `core/audio_capture.py` | QThread audio capture + STT with PyQt signals |
| `LLMClient` | Class | `core/llm_client.py` | Multi-provider LLM with streaming support |
| `MainWindow` | Class | `ui/main_window.py` | Main control panel with config UI |
| `OverlayWindow` | Class | `ui/overlay_window.py` | Transparent caption display with drag bar |

## CONVENTIONS

### Python Style
- **Formatter**: Black (IDE configured)
- **Private methods**: `_method_name` prefix
- **Module docstrings**: Chinese
- **Logging**: Domain-specific (`stt_logger`, `llm_logger`, `system_logger`)

### Configuration
- **Dot-notation access**: `config.get("llm.provider.openai.api_key")`
- **Property accessors**: `config.llm_mode`, `config.stt_model`
- **Provider abstraction**: `llm.provider.{openai,ollama,lmstudio}` with shared keys

### Signal/Slot Architecture
- `AudioCapture` emits: `transcription_ready`, `real_time_update`, `recording_started`, `volume_update`
- `MainWindow` connects all signals for coordination
- Cross-thread communication via PyQt signals (not asyncio)

## ANTI-PATTERNS (THIS PROJECT)

| Pattern | Location | Issue |
|---------|----------|-------|
| `global _config` | `core/config.py:212` | Global mutable state — limits testability |
| Hardcoded paths | `test/test_transcribe.py:81` | `E:/workspace/...` — not portable |
| `print()` debugging | Multiple test files | Should use `logging` module |
| `time.sleep()` | `test/monitor_audio.py:31` | Blocking call in event-driven code |
| No formal tests | `test/` directory | Manual diagnostic scripts, no assertions |

## UNIQUE STYLES

1. **Chinese-first**: Documentation, UI text, comments in Chinese
2. **Dated plan docs**: `docs/plans/YYYY-MM-DD-feature-name.md`
3. **Debug audio naming**: `debug_YYYYMMDD_HHMMSS_#N_debug.wav`
4. **Multi-provider LLM**: Runtime switching via `switch_llm_from_file()`
5. **Async bridge**: `asyncio.new_event_loop()` in QThread (not pure asyncio)
6. **WASAPI loopback**: Windows-specific system audio capture via `pyaudiowpatch`

## COMMANDS

```bash
# Run application
python app.py
# Or use Windows launcher (auto-checks config/deps)
start.bat

# Install dependencies
pip install -r requirements.txt

# PyTorch GPU (CUDA 11.8)
pip install torch==2.5.1+cu118 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cu118

# PyTorch GPU (CUDA 12.8)
pip install torch==2.7.1+cu128 torchaudio==2.7.1+cu128 --index-url https://download.pytorch.org/whl/cu128

# Run manual test scripts
python test/test_audio.py
python test/test_transcribe.py
```

## NOTES

- **Config**: Never commit `config.yaml` — use `config.yaml.template` as base
- **Test scripts**: Standalone executables, not pytest/unittest — run manually
- **Overlay window**: F12 toggles visibility, drag bar for repositioning
- **STT latency**: Use `base` or `tiny` Whisper model if GPU is slow
- **Audio device**: Check `input_device_index` in config if no audio captured
- **Git worktrees**: `.worktrees/` directory used for parallel feature work
