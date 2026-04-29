## ADDED Requirements

### Requirement: Follow-up suggestions generated after answer

The system SHALL generate follow-up question suggestions after each answer is completed.

#### Scenario: Trigger follow-up generation

- **WHEN** an answer generation completes successfully
- **THEN** the system SHALL asynchronously generate follow-up suggestions

#### Scenario: No follow-up when disabled

- **WHEN** config `conversation.enable_followup` is false
- **THEN** no follow-up suggestions SHALL be generated

### Requirement: Follow-up suggestions based on current context

The system SHALL generate suggestions considering the current question and answer.

#### Scenario: Suggestions reference current topic

- **WHEN** follow-up suggestions are generated
- **THEN** suggestions SHALL be relevant to the current question-answer topic

#### Scenario: Suggestions consider conversation history

- **WHEN** follow-up suggestions are generated
- **THEN** suggestions SHALL consider previous conversation context if available

### Requirement: Follow-up suggestions format

The system SHALL format suggestions as a numbered list of potential questions.

#### Scenario: Suggestions output format

- **WHEN** follow-up suggestions are generated
- **THEN** the output SHALL be a list of 2-3 suggested follow-up questions

#### Scenario: Each suggestion marked as reference

- **WHEN** suggestions are displayed
- **THEN** each suggestion SHALL be prefixed with "仅供参考"

### Requirement: Follow-up suggestions optional display

The system SHALL provide UI option to show or hide follow-up suggestions.

#### Scenario: Default hidden in UI

- **WHEN** follow-up suggestions are generated
- **THEN** they SHALL be stored but not automatically displayed in overlay

#### Scenario: User can toggle display

- **WHEN** user requests to view follow-up suggestions
- **THEN** the suggestions SHALL be displayed in a collapsible section

### Requirement: Follow-up suggestions independent LLM call

The system SHALL generate suggestions via a separate LLM call from the main answer.

#### Scenario: Separate API call

- **WHEN** follow-up generation is triggered
- **THEN** it SHALL use a separate `generate()` call, not the main answer stream

#### Scenario: Non-blocking generation

- **WHEN** follow-up generation starts
- **THEN** it SHALL NOT block the main answer display or user interaction

### Requirement: Follow-up prompt structure

The system SHALL use a dedicated prompt template for follow-up generation.

#### Scenario: Follow-up prompt includes context

- **WHEN** follow-up prompt is built
- **THEN** it SHALL include the current question, answer, and history context

#### Scenario: Follow-up prompt requests interview-style questions

- **WHEN** follow-up prompt is built
- **THEN** it SHALL instruct the LLM to generate interview-style probing questions