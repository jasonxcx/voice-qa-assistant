# Document Path Persistence

## ADDED Requirements

### Requirement: Document path is persisted to config
The system SHALL store the selected document file path in `config.document.path` immediately after successful file selection and parsing.

#### Scenario: Path persisted after file selection
- **WHEN** user selects a valid markdown file via the file browser dialog
- **THEN** the system SHALL parse the file, store its path in `config.document.path`, and save the config file

#### Scenario: Path restored on next startup
- **WHEN** the application starts and `config.document.path` contains a non-empty path
- **THEN** the system SHALL validate the file exists, auto-load and parse the document if valid, and display the path with a green checkmark indicator

### Requirement: Document path validation on load
The system SHALL validate that the persisted file path exists on disk before attempting to load it.

#### Scenario: Valid path auto-loaded
- **WHEN** `config.document.path` points to an existing file on startup
- **THEN** the system SHALL auto-load the document silently and display a green checkmark in the UI

#### Scenario: Invalid path shows error state
- **WHEN** `config.document.path` points to a file that does not exist on disk
- **THEN** the system SHALL display a red warning icon, show "文件未找到" tooltip, and prominently show the Browse button

### Requirement: Clear document action
The system SHALL allow users to clear the stored document path, resetting to "no document loaded" state.

#### Scenario: Clear document resets state
- **WHEN** user clicks the "Clear document" button
- **THEN** the system SHALL set `config.document.path` to empty string, save config, clear `resume_data` from memory, and reset the UI to "No document" state

### Requirement: Document path is editable
The system SHALL allow users to directly edit the document path in a text field, in addition to using the file browser.

#### Scenario: Manual path entry
- **WHEN** user types a valid file path directly into the document path field and presses Enter
- **THEN** the system SHALL validate the path, parse the file if valid, update `config.document.path`, and update the UI indicator

### Requirement: File browser dialog for path selection
The system SHALL open a native file dialog when user clicks the Browse button, defaulting to the last used directory.

#### Scenario: Browse button opens file dialog
- **WHEN** user clicks the Browse button next to the document path field
- **THEN** the system SHALL open a native file picker dialog filtered to `.md` and `.markdown` files, starting from the current `config.document.path` directory if it exists
