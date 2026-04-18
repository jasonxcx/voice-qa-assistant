# UI Full Config Panel

## ADDED Requirements

### Requirement: All config options have corresponding UI controls
The system SHALL provide a UI control (combobox, line edit, slider, checkbox, or button) for every configuration key in `config.yaml`.

#### Scenario: Config key coverage
- **WHEN** user opens any settings tab
- **THEN** every config key relevant to that tab SHALL have a visible and functional UI control

### Requirement: Basic and Advanced configuration tiers
The system SHALL group configuration options into two visibility tiers: Basic (always visible) and Advanced (collapsed by default).

#### Scenario: Basic options always visible
- **WHEN** user opens any settings tab
- **THEN** all Basic-tier options SHALL be visible without any expansion interaction

#### Scenario: Advanced options collapsed by default
- **WHEN** user opens any settings tab
- **THEN** all Advanced-tier options SHALL be hidden inside a collapsed `QGroupBox.setCheckable(True)` expander labeled "高级设置"

#### Scenario: Advanced options revealed on expand
- **WHEN** user clicks to expand the "高级设置" expander
- **THEN** the system SHALL reveal all Advanced-tier options for that section

### Requirement: Basic tier includes common settings
The Basic tier SHALL include: LLM mode, LLM model, LLM base URL, LLM API key, STT model, STT device, audio source (mic/speaker), audio device, and document path.

### Requirement: Advanced tier includes expert tunables
The Advanced tier SHALL include: `stt.auto.*` thresholds (volume_threshold, voice_ratio, silence_ratio, noise_alpha, pause_seconds, min_sentence_seconds, max_sentence_seconds), `stt.local.compute_type`, `stt.download.mirror`, `stt.download.cache_dir`, `stt.language`, `stt.hotwords`, and all `ui.keyboard_hotkey.*` entries.

### Requirement: Immediate apply for audio device changes
The system SHALL apply audio device configuration changes immediately without requiring model restart.

#### Scenario: Audio device change takes effect immediately
- **WHEN** user selects a different audio device from the combobox
- **THEN** the system SHALL call `restart_monitoring()` and the new device SHALL be used for the next capture session without requiring app restart

### Requirement: Toggle-required for model changes
The system SHALL indicate that STT model, device, and compute type changes require stopping and restarting listening.

#### Scenario: Model change requires toggle feedback
- **WHEN** user changes STT model, device, or compute type
- **THEN** the system SHALL show a status indicator that model changes take effect on next start/stop cycle, not immediately

### Requirement: Save + switch for LLM URL changes
The system SHALL apply LLM base URL and model changes when user clicks the Save button, via `llm_client.switch_mode()`.

#### Scenario: LLM URL change applied on save
- **WHEN** user modifies LLM base URL or model name and clicks Save
- **THEN** the system SHALL call `config.save()` followed by `llm_client.switch_mode()` and display a success confirmation

### Requirement: Config auto-save with debouncing
The system SHALL auto-save config changes to disk, but debounce rapid slider changes to avoid excessive disk I/O.

#### Scenario: Slider changes debounced
- **WHEN** user drags a slider control rapidly (e.g., volume_threshold)
- **THEN** the system SHALL batch config saves, writing to disk no more than once per 500ms

### Requirement: Reset to defaults per section
The system SHALL provide a "Reset to defaults" button for each settings section that restores all values in that section to `config.yaml.template` defaults.

#### Scenario: Reset restores template defaults
- **WHEN** user clicks "Reset to defaults" in a section
- **THEN** the system SHALL load all values from the template, apply them to the UI controls and config, and save

### Requirement: Config options have tooltips
The system SHALL display a descriptive tooltip for every config option explaining its purpose and effect.

#### Scenario: Tooltip shown on hover
- **WHEN** user hovers over a config control
- **THEN** the system SHALL display a tooltip explaining what that setting controls, its valid range, and any side effects
