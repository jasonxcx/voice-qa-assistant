# PySide6 Migration

## ADDED Requirements

### Requirement: Replace all PyQt5 imports with PySide6
The system SHALL replace all `from PyQt5 import *` statements with equivalent `PySide6.QtCore`, `PySide6.QtWidgets`, and `PySide6.QtGui` imports throughout the codebase.

#### Scenario: PyQt5 imports removed
- **WHEN** code review is performed
- **THEN** no file SHALL contain `from PyQt5 import` or `import PyQt5`

#### Scenario: PySide6 imports present
- **WHEN** any GUI file needs Qt components
- **THEN** it SHALL import from `PySide6.QtCore`, `PySide6.QtWidgets`, and `PySide6.QtGui`

### Requirement: Replace pyqtSignal with Signal
The system SHALL replace all `pyqtSignal` class attribute declarations with `Signal` from `PySide6.QtCore`.

#### Scenario: Signal migration
- **WHEN** a signal is declared on a Qt class
- **THEN** it SHALL use `Signal` (from PySide6) instead of `pyqtSignal`

### Requirement: PySide6-compatible signal/slot connections
The system SHALL ensure all signal/slot connections work correctly under PySide6's signaling mechanism.

#### Scenario: Signals emit and slots receive
- **WHEN** any signal is emitted anywhere in the application
- **THEN** all connected slots SHALL be invoked with the correct arguments

### Requirement: requirements.txt updated
The system SHALL replace the `PyQt5` dependency with `PySide6` in `requirements.txt`.

#### Scenario: requirements.txt contains PySide6
- **WHEN** a fresh environment installs from requirements.txt
- **THEN** `PySide6` SHALL be installed and `PyQt5` SHALL NOT be installed

### Requirement: API compatibility adapters where needed
The system SHALL handle known PyQt5-to-PySide6 API differences via compatibility shims or conditional logic where necessary.

#### Scenario: Known differences handled
- **WHEN** code encounters a known PyQt5/PySide6 API difference (e.g., `QStringList` handling, some widget constructors)
- **THEN** the code SHALL use a PySide6-compatible approach

### Requirement: Both windows ported to PySide6
The system SHALL port both `MainWindow` and `OverlayWindow` to use PySide6 widgets exclusively.

#### Scenario: MainWindow uses PySide6
- **WHEN** the main window is instantiated
- **THEN** it SHALL be a `PySide6.QtWidgets.QMainWindow`

#### Scenario: OverlayWindow uses PySide6
- **WHEN** the overlay window is instantiated
- **THEN** it SHALL be a `PySide6.QtWidgets.QWidget` with PySide6 window flags

### Requirement: QSS stylesheets compatible with PySide6
The system SHALL ensure all QSS (Qt Style Sheets) syntax is valid for PySide6.

#### Scenario: Stylesheets apply correctly
- **WHEN** the application loads and applies QSS stylesheets
- **THEN** no QSS parsing errors SHALL occur and all styled elements SHALL render as expected
