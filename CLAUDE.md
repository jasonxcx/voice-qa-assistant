# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Quick Start

```bash
# Install dependencies (PyTorch with CUDA 11.8 for GPU acceleration)
pip install torch==2.5.1+cu118 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cu118
pip install -r requirements.txt

# Configure VB-Cable for system audio capture (see README.md)
# Edit config.yaml with your API keys

# Run the application
python app.py
```

## Project Architecture

**Interview Helper** is a PyQt5-based desktop application that captures meeting audio (via VB-Cable system loopback), transcribes it to text using Faster-Whisper (GPU-accelerated), and generates interview answers using LLMs.

### Core Module Structure

```
interviewHelper/
├── app.py                    # Entry point - Qt application setup
├── config.yaml               # Configuration (LLM mode, audio devices, STT settings)
├── ui/                       # PyQt5 UI components
│   ├── main_window.py        # Main configuration window
│   ├── overlay_window.py     # Floating subtitle/caption window
│   └── styles.py             # CSS-like stylesheets
├── core/                     # Business logic
│   ├── config.py             # YAML config loader/saver
│   ├── audio_capture.py      # WASAPI loopback capture + Faster-Whisper STT
│   ├── llm_client.py         # Multi-LLM client (Qwen, Ollama, LM Studio)
│   ├── resume_parser.py      # Markdown resume parser
│   └── logger.py             # Colored logging to console + files
└── test/                     # Audio testing utilities
```

### Key Architectural Patterns

1. **Qt Signal/Slot Architecture**: `AudioCapture` uses `pyqtSignal` to communicate with the UI:
   - `transcription_ready` - completed transcription
   - `real_time_update` - streaming transcription
   - `recording_started/stopped` - state changes
   - `volume_update` - real-time volume meter

2. **Model-View separation**: The `Config` class is the model, UI widgets are the view. Configuration persists to `config.yaml`.

3. **Multi-tenant LLM Client**: `LLMClient` wraps `QwenClient`, `OllamaClient`, and `LMStudioClient` via a unified interface. The LMStudio client includes sophisticated parsing for Qwen3 thinking process output.

4. **Async/await throughout**: All LLM calls use `httpx.AsyncClient` for non-blocking HTTP requests.

5. **WASAPI Loopback Audio**: Uses `pyaudiowpatch` (a maintained fork of `pyaudio`) to capture system audio instead of microphone input. Default device index is configured in `config.yaml`.

6. **STT with Faster-Whisper**: Audio is captured via PyAudio stream, buffered until silence is detected (1.5s), then transcribed using Faster-Whisper with GPU acceleration.

## Configuration

Edit `config.yaml` to configure:
- `llm.mode`: "qwen" (cloud), "ollama" (local), or "lmstudio" (local)
- `stt.model`: tiny/base/small/medium/large-v2
- `audio.input_device_index`: VB-Cable output device index (find via `python -m sounddevice`)
- `ui.overlay_height/width_ratio/font_size`: Caption window appearance

## Common Tasks

- **Add a new LLM provider**: Create a class extending `BaseLLMClient` in `core/llm_client.py`, implement `generate()` and `generate_stream()`, add to `LLMClient._create_client()`.
- **Modify caption window behavior**: Edit `ui/overlay_window.py` (DragBar, CaptionHistory, OverlayWindow classes).
- **Change parsing logic**: Modify `core/resume_parser.py` for different Markdown resume formats.

## Troubleshooting

- **No audio capture**:
  - Check Windows sound settings - ensure the correct output device is selected
  - Run `python -m sounddevice` to list available devices
  - Try different `input_device_index` values in config.yaml (device 9 is often NVIDIA HDMI loopback)
  - Verify volume meter shows activity in the main window

- **Audio detected but no transcription**:
  - Lower `silence_threshold` in `audio_capture.py` (default 0.01)
  - Reduce `silence_duration_threshold` (default 1.5s) - triggers transcription after this duration of silence

- **STT slow/incorrect**:
  - Try smaller model (tiny/base) in config.yaml
  - Use CPU mode if GPU runs out of memory (`stt.device: cpu`)

- **LM Studio/Qwen3 thinking process**: The `LMStudioClient._extract_answer_from_qwen3_content()` method handles output filtering

- **Test audio device**: Run `python test/test_loopback.py` to verify the selected device captures system audio
