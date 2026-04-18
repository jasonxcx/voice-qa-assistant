## Context

The current main window (`ui/main_window.py`) is a PyQt5 application built around 2008-era UI patterns: vertical stack of QGroupBox sections, inconsistent inline styles, and config options buried in YAML files. The overlay window (`ui/overlay_window.py`) uses hardcoded inline RGBA values that diverge from the shared stylesheet. Three user-facing problems drive this change:

1. **Visual**: The UI feels dated — solid-color groupboxes with borders, inconsistent button styles, no visual hierarchy
2. **Configuration**: All behavior-critical settings live in `config.yaml`, requiring YAML editing (error-prone, no validation)
3. **Document flow**: Resume document must be re-selected every session — path is never persisted

The app runs on Windows with **PySide6** (Qt for Python, LGPL-licensed — migrated from PyQt5 for commercial compatibility), uses Faster-Whisper for STT, and supports three LLM providers (OpenAI-compatible API, Ollama, LM Studio). Config is a singleton with dot-notation access.

## Goals / Non-Goals

**Goals:**
- Create a visually cohesive, modern UI for both MainWindow and OverlayWindow
- Expose every config option through UI controls with appropriate input widgets
- Persist document path between sessions with auto-restore on startup
- Unify styling approach so both windows share color constants and button patterns

**Non-Goals:**
- Light/dark theme switching (single dark theme, but modernized)
- Config import/export or backup functionality
- Custom CSS injection for power users
- Non-Qt approaches (e.g., web-based UI, Tkinter)
- Changing any backend business logic (STT, LLM, audio capture remain unchanged)

> **License Note**: PySide6 uses LGPL — dynamic linking is permitted as long as Qt binaries are not modified. This permits closed-source commercial distribution.

## Decisions

### 1. Layout: Tabbed Navigation with Settings Panel (vs. Card-based)

**Decision**: Use `QTabWidget` for top-level navigation with 4 tabs: **主面板 (Main)**, **LLM 设置**, **STT 设置**, **显示设置**.

**Rationale**: The current 5-groupbox vertical stack creates deep nesting and forces scrolling. A tabbed interface groups settings by concern (behavior vs. display) and keeps all controls accessible within 1-2 clicks. Card-based was rejected because it would still require vertical scrolling and doesn't naturally group "related actions" (LLM settings belong together).

**Alternatives considered**:
- *Card-based vertical stack*: Rejected — still a vertical stack, just with cards instead of groupboxes. Doesn't reduce cognitive load.
- *Sidebar navigation*: Rejected — requires horizontal space that a narrow tool window doesn't have; overkill for 4 logical groups.
- *Single scrollable form*: Rejected — too many controls (40+ options); user would constantly scroll past irrelevant sections.

### 2. Visual Style: Modern Dark Theme with Elevated Cards (vs. Flat/Groupbox)

**Decision**: Define a new dark theme using elevated card surfaces with subtle shadows, rounded corners (8px), and a restrained accent color palette. Replace all inline widget styles with shared QSS stylesheet classes.

**New color palette**:
```
Background (main):     #0F0F0F  (near-black, darker than current #1E1E1E)
Surface (cards):       #1A1A1A  (elevated surface)
Surface hover:         #242424  (interactive hover)
Border subtle:         #2A2A2A  (card/section borders)
Border focus:          #3D3D3D  (focused element borders)
Text primary:          #FFFFFF
Text secondary:        #8A8A8A  (labels, hints)
Text muted:            #5C5C5C  (disabled)
Accent primary:         #6366F1  (indigo — replaces #0078D4 Windows blue)
Accent hover:           #818CF8  (lighter indigo)
Accent active:          #4F46E5  (darker indigo pressed)
Success:               #22C55E  (green — status indicators)
Warning:               #F59E0B  (amber)
Error:                 #EF4444  (red)
```

**Rationale**: The current `#0078D4` Windows-blue accent feels dated. Indigo (`#6366F1`) is modern, widely used in developer tools (Vercel, Linear, Raycast). The near-black background creates visual depth with elevated card surfaces — a common pattern in modern desktop apps (Discord, Slack, VS Code dark themes).

**Button styles** (unified across both windows):
```css
/* Primary button (start, save) */
background: #6366F1; color: #fff; border: none; border-radius: 8px; padding: 10px 20px;

/* Secondary button (refresh, toggle) */
background: #1A1A1A; color: #fff; border: 1px solid #2A2A2A; border-radius: 8px; padding: 10px 16px;

/* Danger button (clear, reset) */
background: rgba(239,68,68,0.15); color: #EF4444; border: none; border-radius: 6px; padding: 6px 12px;

/* Icon button */
background: transparent; color: #8A8A8A; border: none; border-radius: 6px; padding: 8px;
```

**Inline style extraction**: `main_window.py` has inline styles on `start_btn`, `caption_toggle_btn`, `log_btn`, `save_btn`, `clear_log_btn` — these will be moved to `styles.py` under the new QSS class system.

### 3. Config UI Exposure: Basic/Advanced Split with Immediate Apply

**Decision**: Group config options into two visibility tiers:
- **Basic** (shown by default): LLM mode/model/URL/key, STT model/device, audio source/device, document path, overlay visibility hotkey
- **Advanced** (collapsible `QExpander` or separate tab): `stt.auto.*` thresholds, compute type, download mirror, language, hotwords, all keyboard hotkeys, volume threshold

**Per-option apply behavior** (verified from code analysis):

| Apply Type | Config Keys | How It Works |
|------------|-------------|--------------|
| **Immediate** | `audio.output_device_index`, `audio.input_device_index`, `audio.use_microphone` | Calls `restart_monitoring()` right away — no model reload needed |
| **Immediate** | `ui.transcription.manual_mode`, `ui.font_size` | Direct signal/slot, no model involvement |
| **Toggle Required** | `stt.model`, `stt.local.device`, `stt.local.compute_type` | Takes effect on next `audio_capture.start()` — user must stop and restart listening |
| **Save + Switch** | `llm.base_url`, `llm.model` (OpenAI/Ollama), provider configs | `config.save()` + `llm_client.switch_mode()` — happens on Save button click |
| **App Restart** | `llm.mode` (provider switch) | Requires save + restart or explicit `switch_mode()` call |

**Rationale**: Exposing all 40+ options simultaneously would overwhelm users. The 80/20 rule applies — ~20% of options cover 80% of use cases. Advanced options stay accessible but don't clutter the default view. The apply-behavior table above clarifies UX: audio changes are instant, model changes require toggle, LLM URL changes require explicit save.

**Add to `config.yaml.template`**:
```yaml
document:
  path: ""  # Persisted markdown resume path

audio:
  use_microphone: false  # currently missing from template
  input_device_index: 1
  output_device_index: 5
```

### 4. Document Path Persistence: Store Path + Validate + Auto-load

**Decision**:
1. Add `document.path` to `config.yaml` (not in template initially — empty means "no document")
2. When user selects a file via `QFileDialog`, validate it exists, parse it, store path to config, save config
3. On `MainWindow.__init__`, read `config.document.path`, validate with `os.path.exists()`, if valid → silently auto-load and show checkmark in UI; if invalid/missing → show "No document" state
4. Add a "Clear document" button (inverse action) that sets `document.path` to `""` and clears `resume_data`

**Rationale**: Users shouldn't need to re-select their resume on every launch. The "upload" mental model is wrong for a persistent desktop app — it's a file path reference, not a temporary upload. `QFileDialog` is still used for browsing, but the result is a persistent reference.

**Path validation UX**:
- If file exists → show green checkmark + truncated path
- If file not found → show red warning icon + "File not found" + "Browse" button prominently shown
- No auto-download or recovery — user must re-browse

### 5. Window State Persistence: Save MainWindow Geometry

**Decision**: On `MainWindow` close, save `saveGeometry()` / `saveState()` to config. On startup, restore if valid. This is a natural extension alongside document path persistence.

**Add to `config.yaml`**:
```yaml
ui:
  window_geometry: null  # Base64 encoded geometry, null = default
  window_state: null     # Normal/maximized state
```

**Rationale**: Users who resize the window to a specific shape expect it to stay that way. This is standard desktop app behavior (Qt provides the API for free).

### 6. Overlay Window Style Unification

**Decision**: Extract all overlay inline RGBA colors to shared constants in `styles.py`. Adopt the new indigo accent. The overlay's transparency and `WA_TranslucentBackground` are preserved — only color values change.

**Shared constants to add to `styles.py`**:
```python
OVERLAY_BG_SOLID = "rgba(15, 15, 15, 230)"      # When hovering (solid version of transparent bg)
OVERLAY_CAPTION_QUESTION = "#90CAF9"  # Keep existing — not changing content colors
OVERLAY_CAPTION_ANSWER = "#81C784"    # Keep existing
OVERLAY_SHADOW = "rgba(0, 0, 0, 180)" # Shadow color
OVERLAY_LISTEN_ACTIVE = "rgba(76, 175, 80, 150)"   # Green
OVERLAY_LISTEN_INACTIVE = "rgba(244, 67, 54, 150)"  # Red
```

**Rationale**: The overlay needs different background handling (transparent + hover-reveal) so it can't use the same card system, but it should share the same *color language* — indigo accent instead of mismatched blue/green inline values.

### 7. New UI Widgets to Add

| Widget | Type | Purpose |
|--------|------|---------|
| Document path display | `QLineEdit` + `QPushButton` (Browse) | Editable path field with browse action |
| Path status indicator | `QToolButton` with icon | Green checkmark / red warning based on file existence |
| Advanced expander | `QGroupBox.setCheckable(True)` | PySide6-compatible collapsible section for 15+ expert options |
| Reset-to-defaults | `QPushButton` per-section | Reverts a settings section to config.yaml.template defaults |
| Volume slider | `QSlider` | Replaces volume bar label for audio input level |
| STT progress | `QProgressBar` | Shows model download/loading progress |
| Loading overlay | `QWidget` overlay on main window | Disables UI during model loading |

## Risks / Trade-offs

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **PySide6 migration breaks API compatibility** | Low | PySide6 vs PyQt5 have minor API differences (e.g., `pyqtSignal` vs `Signal`) | Use compatibility shim or bulk replace; test signal/slot connections first |
| **Inline style extraction breaks existing appearance** | Medium | UI looks different in ways not intended | Test both windows thoroughly; preserve functional behavior first, adjust colors second |
| **Tab navigation breaks muscle memory** | Low | Users familiar with groupbox order must re-learn | Keep tab order consistent with current groupbox top-to-bottom order |
| **Exposing all config options creates decision fatigue** | Medium | Users confused by too many choices | Strong Basic/Advanced curation; tooltips on every option explaining what it does |
| **Path persistence breaks if file moved/deleted** | High | App shows stale state or crashes | Explicit file existence check on load; clear error UI with "re-browse" action |
| **Config auto-save on every change creates disk I/O** | Low | SSD makes this negligible; batch saves every 500ms if needed | Use Qt's `QTimer` to debounce rapid slider changes |
| **Model reload requires UI state reset** | Medium | STT model switch requires cleanup + reload + UI feedback | Implement `_reload_stt_model()` with proper signal/slot flow; show progress |

## Migration Plan

1. **Phase 1 — Styling foundation** (lowest risk)
   - Add new color palette and QSS classes to `styles.py` alongside existing styles
   - Apply new theme to `OverlayWindow` only (isolated — no logic changes)
   - Verify overlay still works; no functional changes

2. **Phase 2 — MainWindow layout restructure** (medium risk)
   - Create new tab-based skeleton alongside existing groupbox layout
   - Hide old layout, show new layout via feature flag or single assignment
   - Migrate one tab at a time (Main tab first, then LLM, STT, Display)

3. **Phase 3 — Config exposure** (medium risk)
   - Add `document.path` to config schema and template
   - Implement path persistence logic
   - Add UI controls for previously hidden options
   - Wire each control to config change → apply

4. **Phase 4 — Polish and validation** (low risk)
   - Window geometry persistence
   - Form validation feedback
   - Loading states and progress indicators
   - "Clear document" and "Reset to defaults" actions

**Rollback**: Each phase is independently deployable. Phase 1 and 2 are purely visual — git revert restores old appearance. Phase 3 and 4 require config schema migration (add fields, don't remove).

## Open Questions

1. **QTabWidget vs. QStackedWidget + sidebar**: Does the team have a preference on tab vs. icon-sidebar for the 4 sections? (Current decision: QTabWidget for simplicity)
2. ~~**Config apply behavior per option**~~ — **Resolved**: See apply-behavior table in Decision #3. Audio = immediate, model = toggle required, LLM URL = save + switch.
3. **STT model download progress**: Currently `QProgressDialog` during download. Should this move to a dedicated "Downloads" section in the UI, or stay inline?
4. **API key security**: Currently API keys are plain text in config.yaml. Should the UI add an option to mask/cipher keys, or is plaintext acceptable given local-only deployment?
5. **PySide6 migration scope**: Should we migrate existing PyQt5 imports incrementally (file by file) or do a bulk replace? Bulk replace is faster but riskier.
