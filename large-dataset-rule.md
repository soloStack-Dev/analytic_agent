File
  |
  v
Pandas
  |
  v
Dataset metadata
  |
  +--> schema
  +--> statistics
  +--> sample rows
  +--> unique values where appropriate
  |
  v
LLM


The LLM should receive only the information necessary to understand the
dataset and user request.

For example, do not send 500,000 rows to the LLM just to determine that
"Sales" is a numeric column.