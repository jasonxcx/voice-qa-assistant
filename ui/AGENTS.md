# UI MODULE

## OVERVIEW

PyQt5 GUI layer: main control window (config, device selection, transcription log) and transparent overlay caption window (drag/resize, F12 toggle).

## STRUCTURE

```
ui/
├── __init__.py           # Package exports: MainWindow, OverlayWindow, styles
├── main_window.py        # Main control panel (916 lines)
├── overlay_window.py     # Transparent caption display (728 lines)
└── styles.py             # Shared stylesheets: dark theme, status colors
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Main window UI | `main_window.py` | 40+ widgets, config sync, LM Studio API |
| Overlay captions | `overlay_window.py` | Drag bar, corner resize, history navigation |
| Shared stylesheets | `styles.py` | `MAIN_WINDOW_STYLESHEET`, `STATUS_COLORS` |
| Widget custom classes | `overlay_window.py` | `CaptionHistory`, `DragBar`, `OverlayWindow` |

## CONVENTIONS

### Module Exports
```python
# ui/__init__.py
from .main_window import MainWindow
from .overlay_window import OverlayWindow
from . import styles
```

### Stylesheet Pattern
```python
# styles.py
MAIN_WINDOW_STYLESHEET = """
QWidget {
    background-color: #1e1e1e;
    color: #ffffff;
}
"""

STATUS_COLORS = {
    "idle": "#808080",
    "listening": "#00ff00",
    "generating": "#ffff00",
    "error": "#ff0000"
}
```

### Signal Connections (MainWindow)
```python
audio_capture.transcription_ready.connect(self.on_transcription)
audio_capture.volume_update.connect(self.update_volume_indicator)
llm_client.answer_generated.connect(self.display_answer)
```

### Overlay Window Control
```python
# F12 hotkey toggles visibility
overlay.toggle_visibility()

# Drag bar repositioning
overlay.move(x, y)

# Corner resize detection
if mouse_in_corner():
    set_cursor(Qt.SizeFDiagCursor)
```

## ANTI-PATTERNS (THIS MODULE)

| Pattern | Location | Issue |
|---------|----------|-------|
| Large file size | `main_window.py:916` | Should extract components |
| PyQt5 method overrides | `overlay_window.py` | Parameter name mismatch with base class |
| LSP type errors | Multiple files | PyQt5 stubs incomplete |

## UNIQUE STYLES

1. **Transparent overlay**: `WA_TranslucentBackground` + `WA_NoSystemBackground`
2. **Drag bar architecture**: Separate widget for repositioning
3. **Corner resize detection**: Manual mouse tracking with `QTimer`
4. **F12 global hotkey**: System-wide visibility toggle

## NOTES

- **LSP errors**: PyQt5 stubs incomplete — many `Qt.AlignCenter`, `Qt.LeftButton` false positives
- **Method override warnings**: `closeEvent`, `mousePressEvent` parameter names differ from base (`a0` vs `event`) — safe to ignore
- **Overlay positioning**: Bottom-right corner by default, draggable via top bar
- **Status colors**: Defined in `styles.py`, used across both windows
