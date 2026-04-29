## ADDED Requirements

### Requirement: History storage supports Q&A pairs

The system SHALL maintain an in-memory list of question-answer pairs for the current conversation session.

#### Scenario: Initial empty history

- **WHEN** a new conversation session starts
- **THEN** the history list SHALL be empty

#### Scenario: Add Q&A pair after answer generation

- **WHEN** an answer is successfully generated for a question
- **THEN** the question and answer pair SHALL be appended to the history list

### Requirement: History supports configurable maximum length

The system SHALL limit the number of stored Q&A pairs based on configuration.

#### Scenario: Default maximum length is 5

- **WHEN** no custom configuration is provided
- **THEN** the system SHALL keep at most 5 Q&A pairs in history

#### Scenario: Custom maximum length from config

- **WHEN** config `conversation.max_history_length` is set to a value N
- **THEN** the system SHALL keep at most N Q&A pairs in history

#### Scenario: Sliding window eviction

- **WHEN** history exceeds the configured maximum length
- **THEN** the oldest Q&A pair SHALL be removed from history

### Requirement: History can be cleared

The system SHALL provide a method to clear all stored Q&A pairs.

#### Scenario: Clear history on user action

- **WHEN** user triggers "Start new session" action
- **THEN** all Q&A pairs SHALL be removed from history

#### Scenario: Clear history returns empty state

- **WHEN** history is cleared
- **THEN** subsequent retrieval SHALL return an empty list

### Requirement: History retrieval provides formatted output for prompt

The system SHALL provide a method to format history for LLM context injection.

#### Scenario: Get formatted history for prompt

- **WHEN** `get_history_for_prompt()` is called
- **THEN** history SHALL be formatted as Q&A pairs with section header

#### Scenario: Formatted history ordered chronologically

- **WHEN** history is formatted for prompt
- **THEN** pairs SHALL be ordered oldest to newest (chronological order)

### Requirement: Handle edge cases gracefully

The system SHALL handle edge cases without errors.

#### Scenario: max_history_length is 0

- **WHEN** config `conversation.max_history_length` is 0
- **THEN** no history SHALL be stored or injected, and followup suggestions SHALL be disabled

#### Scenario: Streaming answer failure

- **WHEN** answer generation fails mid-stream
- **THEN** the incomplete answer SHALL NOT be stored in history