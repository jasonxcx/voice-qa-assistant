# UI Visual Redesign

## ADDED Requirements

### Requirement: Tabbed navigation layout
The system SHALL use `QTabWidget` for top-level navigation with exactly 4 tabs: 主面板 (Main), LLM 设置, STT 设置, and 显示设置.

#### Scenario: Four tabs visible
- **WHEN** user opens the main window
- **THEN** exactly 4 tabs SHALL be visible: 主面板, LLM 设置, STT 设置, 显示设置

#### Scenario: Tab content switches correctly
- **WHEN** user clicks on a tab
- **THEN** the content area SHALL display only the controls relevant to that tab

### Requirement: Modern dark color palette
The system SHALL use a dark color palette with near-black background (#0F0F0F), elevated surface cards (#1A1A1A), and indigo accent (#6366F1).

#### Scenario: Color palette applied
- **WHEN** the new theme is active
- **THEN** the main background SHALL be #0F0F0F, card surfaces SHALL be #1A1A1A, and primary accent SHALL be #6366F1

### Requirement: Unified button styles
The system SHALL define three button styles (Primary, Secondary, Danger) shared across both MainWindow and OverlayWindow.

#### Scenario: Primary button style
- **WHEN** a Primary button (start, save) is rendered
- **THEN** it SHALL have background #6366F1, white text, no border, 8px border-radius, 10px 20px padding

#### Scenario: Secondary button style
- **WHEN** a Secondary button (refresh, toggle) is rendered
- **THEN** it SHALL have background #1A1A1A, white text, 1px solid #2A2A2A border, 8px border-radius, 10px 16px padding

#### Scenario: Danger button style
- **WHEN** a Danger button (clear, reset) is rendered
- **THEN** it SHALL have background rgba(239,68,68,0.15), text #EF4444, no border, 6px border-radius, 6px 12px padding

### Requirement: All inline widget styles extracted to stylesheet
The system SHALL replace all hardcoded inline `setStyleSheet()` calls on individual widgets with shared QSS class selectors in `styles.py`.

#### Scenario: No inline style overrides on buttons
- **WHEN** any button widget is instantiated
- **THEN** its style SHALL come from the global stylesheet classes, not from inline `setStyleSheet()` calls

### Requirement: Overlay window shares color constants
The system SHALL extract OverlayWindow inline RGBA color values to shared constants in `styles.py`, ensuring visual consistency with MainWindow.

#### Scenario: Overlay uses shared constants
- **WHEN** the OverlayWindow renders any colored element
- **THEN** the color values SHALL reference shared constants from `styles.py`, not hardcoded inline strings

### Requirement: Modern card-based section containers
The system SHALL use elevated card surfaces (subtle border + slight background contrast) instead of traditional QGroupBox with thick borders for section containers.

#### Scenario: Card container appearance
- **WHEN** a settings section is rendered
- **THEN** it SHALL appear as a card with background #1A1A1A on #0F0F0F background, with subtle #2A2A2A border and 8px border-radius

### Requirement: Consistent font sizing
The system SHALL use consistent font sizing: 15px bold for tab titles, 14px for section headers, 13px for labels, 12px for body text.

### Requirement: Loading overlay during model initialization
The system SHALL display a semi-transparent loading overlay on the main window that disables all controls during STT model loading/download.

#### Scenario: Loading overlay shown during model load
- **WHEN** user clicks Start and the STT model is being loaded or downloaded
- **THEN** the system SHALL display a centered loading indicator over the main window UI, preventing interaction with other controls

### Requirement: Volume level as slider not label
The system SHALL replace the static volume percentage label with a `QSlider` widget that provides real-time visual feedback during audio monitoring.

#### Scenario: Volume slider functional
- **WHEN** audio monitoring is active
- **THEN** the volume slider SHALL reflect real-time audio input level and user SHALL be able to observe levels visually

### Requirement: Progress indicator for STT model loading
The system SHALL show a determinate or indeterminate progress indicator (not just button text change) during STT model initialization.

#### Scenario: Progress shown during model load
- **WHEN** the STT model is being loaded (from disk or downloaded)
- **THEN** a progress bar SHALL be displayed indicating the loading state, not merely a text label change on the start button
