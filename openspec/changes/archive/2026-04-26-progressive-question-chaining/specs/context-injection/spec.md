## ADDED Requirements

### Requirement: History context injected into system prompt

The system SHALL append conversation history to the LLM system prompt when generating answers.

#### Scenario: Inject history when history exists

- **WHEN** at least one Q&A pair exists in history
- **THEN** the history SHALL be formatted and appended to the system prompt

#### Scenario: No injection when history is empty

- **WHEN** history is empty or max_history_length is 0
- **THEN** the system prompt SHALL NOT include history section

### Requirement: History format follows structured template

The system SHALL format history using a specific Q&A template for LLM comprehension.

#### Scenario: History format template

- **WHEN** history is injected into prompt
- **THEN** each pair SHALL be formatted as:
  ```
  Q: <question text>
  A: <answer text (truncated)>
  ```

#### Scenario: History section header

- **WHEN** history is injected
- **THEN** the history section SHALL be prefixed with header: `## 前序对话（供参考，理解追问上下文）`

### Requirement: History injection respects sliding window

The system SHALL inject only the most recent N Q&A pairs as configured.

#### Scenario: Inject configured number of pairs

- **WHEN** history contains 10 pairs and max_history_length is 5
- **THEN** only the 5 most recent pairs SHALL be injected

### Requirement: History injection position in prompt

The system SHALL place history context between document information and response rules in the system prompt.

#### Scenario: Prompt structure order

- **WHEN** history is injected
- **THEN** the order SHALL be:
  1. Base system prompt
  2. Document information (if present)
  3. History context (new)
  4. Response rules

### Requirement: History injection can be disabled via config

The system SHALL support disabling history injection via configuration.

#### Scenario: Disable history injection

- **WHEN** config `conversation.max_history_length` is set to 0
- **THEN** no history SHALL be injected into any prompt

### Requirement: History passed through generate methods

The system SHALL accept history parameter in answer generation methods.

#### Scenario: generate_answer_stream accepts history

- **WHEN** `generate_answer_stream()` is called
- **THEN** it SHALL accept an optional `history_context` parameter

#### Scenario: build_system_prompt accepts history

- **WHEN** `build_system_prompt()` is called
- **THEN** it SHALL accept an optional `history_context` parameter