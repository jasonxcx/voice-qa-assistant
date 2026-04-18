## Why

The current main window UI feels outdated and inconsistent: (1) uses a dated dark theme with hardcoded inline styles that diverge from the shared stylesheet, (2) many config options are only accessible via `config.yaml` file with no UI controls, forcing users to edit YAML directly, and (3) document import requires re-selecting the file every session because paths are never persisted. A complete redesign will modernize the experience, make all settings accessible via UI, and remember document paths between sessions.

## What Changes

1. **Complete UI visual redesign** — Replace the current vertical-groupbox stack with a modern tabbed layout; define a cohesive new color scheme and typography; consolidate all inline styles into shared stylesheets
2. **Full config-to-UI exposure** — Every `config.yaml` option gets a corresponding UI control; options are grouped logically (Basic / Advanced); some advanced options (e.g. voice detection thresholds) can be collapsed under a `QGroupBox.setCheckable(True)` expander
3. **Path-based document import with persistence** — Document selection stores the file path in config; on app startup, if a valid path exists in config, the document is auto-loaded silently; users can also edit/browse the path directly
4. **Unified styling between windows** — Overlay window styles are extracted to share color constants and button styles with the main window for visual consistency
5. **PySide6 migration** — Migrate from PyQt5 to PySide6 for LGPL licensing compatibility (required for commercial distribution)

## Capabilities

### New Capabilities
- `document-path-persistence`: Path-based document loading where the path is stored in config and auto-restored on startup. Replaces the current "upload and forget" flow.
- `ui-full-config-panel`: All config options accessible via UI controls (comboboxes, line edits, sliders, checkboxes). Options are grouped: Basic (common settings) and Advanced (expert tunables). Changes take effect immediately or on next session.
- `ui-visual-redesign`: Complete visual refresh of both MainWindow and OverlayWindow. New color palette, modern tabbed layout, consistent button styles, shared style constants. Not incremental styling fixes — a deliberate new look-and-feel.
- `pyside6-migration`: Migrate from PyQt5 to PySide6 (Qt for Python, LGPL) to permit closed-source commercial distribution. Replaces all `PyQt5` imports with `PySide6`, adapts `pyqtSignal` → `Signal`, and uses `PySide6` widgets throughout.

### Modified Capabilities
- *(none — no existing spec behavior is being changed; this is a pure enhancement)*

## Impact

- **All Python files** — Replace `from PyQt5 import *` with `from PySide6.QtWidgets import *`, `from PySide6.QtCore import *`, etc. Replace `pyqtSignal` with `Signal` (class attribute). This is a bulk mechanical change across ~6 files.
- **ui/main_window.py** — Major restructuring: new tabbed layout, new widgets for all config options, document path persistence logic, PySide6 signal/slot adaptation
- **ui/overlay_window.py** — Style alignment: extract inline styles to shared constants, adopt new theme, PySide6 port
- **ui/styles.py** — New theme definition: color palette, button styles, card styles, shared constants (PySide6-compatible QSS)
- **core/config.py** — Add `document.path` config key; existing property-accessors remain unchanged
- **config.yaml.template** — Add `document.path: ""` field; add any missing `audio.*` fields already referenced in code
- **requirements.txt** — Replace `PyQt5` with `PySide6`
- **core/resume_parser.py** — No changes needed (interface unchanged)
