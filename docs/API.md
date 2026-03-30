# NLQE: Public API Reference

**Version**: v1.0.0  
**Last Updated**: March 17, 2026  
**Status**: POC API Design

## Overview

This document describes the public API surface of NLQE. This is what users will import and interact with. Internal implementation details are in [ARCHITECTURE.md](./ARCHITECTURE.md).

---

## Quick Start Pattern

```
from nlqe import QueryEngine, QueryEngineConfig

# 1. Initialize
config = QueryEngineConfig.from_env()  # Loads from .env
engine = QueryEngine(config)

# 2. Load data
engine.load_datasource("./data/sales.parquet")

# 3. Single query
response = engine.query("What was Q3 revenue?")
print(f"Answer: {response.answer}")
print(f"Confidence: {response.confidence_score}")

# 4. Or multi-turn conversation
conversation = engine.start_conversation()
response1 = conversation.query("Show revenue by region")
response2 = conversation.query("Which had the highest?")  # Has context

# 5. Evaluate against golden data
evaluator = engine.create_evaluator("golden_datasets.yaml")
metrics = evaluator.run()
print(f"Accuracy: {metrics.accuracy:.1%}")
```

---

## Main Interface: QueryEngine

The primary class users interact with.

### Initialization

```
QueryEngine(config: QueryEngineConfig)
```

Creates a QueryEngine instance with given configuration. Configuration is typically loaded from environment variables.

**Parameters**:
- `config`: QueryEngineConfig object with API keys and settings

**Raises**:
- `ValueError` if required configuration is missing

**Example**:
```
from nlqe import QueryEngineConfig, QueryEngine

config = QueryEngineConfig(
    openai_api_key="sk-...",
    openai_model="gpt-4",
    max_debug_attempts=3
)
engine = QueryEngine(config)
```

### load_datasource()

```
load_datasource(
    path: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    type: Optional[str] = None
) -> None
```

Load a datasource (parquet, CSV, or DuckDB database).

**Parameters**:
- `path`: File path or connection string
- `name`: Optional display name (inferred from filename if not provided)
- `description`: Optional description of the data
- `type`: Optional type hint ("parquet", "csv", "duckdb"). Inferred from extension if not provided.

**Raises**:
- `FileNotFoundError` if file doesn't exist
- `ValueError` if format is not supported
- `DuckDBError` if data is corrupted

**Returns**: None (modifies engine state)

**Example**:
```
engine.load_datasource("./data/sales.parquet", 
                       description="Monthly sales transactions")
```

### query()

```
query(
    user_query: str,
    context: Optional[str] = None
) -> QueryResponse
```

Execute a single natural language query against the loaded datasource.

**Parameters**:
- `user_query`: Natural language question
- `context`: Optional previous context (for standalone queries)

**Returns**: QueryResponse object

**Raises**:
- `ValueError` if no datasource loaded
- `QueryExecutionError` if query fails after debug attempts
- `OpenAIError` if API call fails

**Example**:
```
response = engine.query("What was revenue in Q3?")
print(response.answer)
print(f"SQL: {response.generated_sql}")
print(f"Confidence: {response.confidence_score}")
```

### start_conversation()

```
start_conversation() -> ConversationManager
```

Begin a multi-turn conversation with preserved context.

**Returns**: ConversationManager instance

**Raises**:
- `ValueError` if no datasource loaded

**Example**:
```
conversation = engine.start_conversation()
r1 = conversation.query("Show me sales by region")
r2 = conversation.query("Which region had the highest sales?")
# r2 understands context from r1
```

### create_evaluator()

```
create_evaluator(
    golden_dataset_path: str
) -> Evaluator
```

Create an evaluator for testing against golden datasets.

**Parameters**:
- `golden_dataset_path`: Path to YAML file with test cases

**Returns**: Evaluator instance

**Raises**:
- `FileNotFoundError` if dataset file not found
- `ValueError` if dataset format is invalid

**Example**:
```
evaluator = engine.create_evaluator("golden_datasets.yaml")
metrics = evaluator.run()
print(f"Accuracy: {metrics.accuracy}")
```

### get_schema()

```
get_schema() -> DataSourceSchema
```

Get the schema of the loaded datasource (read-only).

**Returns**: DataSourceSchema with table and column information

**Example**:
```
schema = engine.get_schema()
for table in schema.tables:
    print(f"Table: {table.name}")
    for col in table.columns:
        print(f"  - {col.name}: {col.type}")
```

---

## Configuration: QueryEngineConfig

Pydantic model for configuration, loads from environment variables.

### Fields

**OpenAI API Settings**:

- `openai_api_key: str` (required)
  - OpenAI API key for authentication
  - Load from: `NLQE_OPENAI_API_KEY` env var
  
- `openai_model: str = "gpt-4"` (optional)
  - Model to use for SQL generation
  - Load from: `NLQE_OPENAI_MODEL`
  
- `openai_temperature: float = 0.0` (optional)
  - Temperature for SQL generation (deterministic)
  - Load from: `NLQE_OPENAI_TEMPERATURE`
  
- `openai_max_tokens: int = 2000` (optional)
  - Maximum tokens per OpenAI response
  - Load from: `NLQE_OPENAI_MAX_TOKENS`

**Query Execution Settings**:

- `query_timeout_seconds: int = 30` (optional)
  - Timeout for DuckDB query execution
  - Load from: `NLQE_QUERY_TIMEOUT_SECONDS`
  
- `max_debug_attempts: int = 3` (optional)
  - Maximum retry attempts for failed queries
  - Load from: `NLQE_MAX_DEBUG_ATTEMPTS`
  - Valid range: 1-10

**Datasource Settings**:

- `datasource_path: Optional[str] = None` (optional at init)
  - Path to datasource (can be set later via load_datasource)
  - Load from: `NLQE_DATASOURCE_PATH`
  
- `datasource_type: Optional[str] = None` (optional)
  - Type hint for datasource ("parquet", "csv", "duckdb")
  - Load from: `NLQE_DATASOURCE_TYPE`

**Operational Settings**:

- `log_level: str = "INFO"` (optional)
  - Logging verbosity (DEBUG, INFO, WARNING, ERROR)
  - Load from: `NLQE_LOG_LEVEL`
  
- `log_queries: bool = True` (optional)
  - Whether to log generated SQL and execution details
  - Load from: `NLQE_LOG_QUERIES`

### Class Methods

```
QueryEngineConfig.from_env() -> QueryEngineConfig
```

Load configuration from environment variables (and .env file if present).

**Example**:
```
# Load from environment
config = QueryEngineConfig.from_env()

# Or from .env file
from dotenv import load_dotenv
load_dotenv()
config = QueryEngineConfig.from_env()
```

### Example Environment File

```
# .env
NLQE_OPENAI_API_KEY=sk-proj-...
NLQE_OPENAI_MODEL=gpt-4
NLQE_OPENAI_TEMPERATURE=0.0
NLQE_QUERY_TIMEOUT_SECONDS=30
NLQE_MAX_DEBUG_ATTEMPTS=3
NLQE_LOG_LEVEL=INFO
NLQE_LOG_QUERIES=true
```

---

## Response Models

### QueryResponse

The response returned from a query or conversation turn.

**Fields**:

- `user_query: str` - Original user question (exact input)
- `generated_sql: str` - SQL that was executed
- `data: List[Dict]` - Raw results as list of dictionaries
- `answer: str` - Natural language summary of results
- `confidence_score: float` - Confidence in answer (0.0-1.0)
- `execution_time_ms: float` - Time spent executing (wall-clock)
- `result_rows: int` - Number of rows returned
- `debug_info: Optional[DebugInfo]` - Info if query required debugging
- `error: Optional[str]` - Error message if query failed

**Example**:
```
response = engine.query("What was Q3 revenue?")

print(f"Question: {response.user_query}")
print(f"SQL Generated: {response.generated_sql}")
print(f"Results ({response.result_rows} rows):")
for row in response.data:
    print(f"  {row}")
print(f"Answer: {response.answer}")
print(f"Confidence: {response.confidence_score:.1%}")
print(f"Time: {response.execution_time_ms:.0f}ms")

if response.debug_info:
    print(f"Required {response.debug_info.attempts} debug attempts")
    
if response.error:
    print(f"ERROR: {response.error}")
```

### DebugInfo

Information about query debugging (only present if debugging occurred).

**Fields**:

- `attempts: int` - Number of retry attempts made
- `errors: List[str]` - Error messages from each attempt
- `modified_sqls: List[str]` - SQL versions tried during debugging
- `first_error: str` - The initial error that triggered debugging
- `final_error: Optional[str]` - Error message if debugging ultimately failed

**Example**:
```
if response.debug_info:
    print(f"Debugging was needed:")
    print(f"  Initial error: {response.debug_info.first_error}")
    print(f"  Retry attempts: {response.debug_info.attempts}")
    for i, sql in enumerate(response.debug_info.modified_sqls):
        print(f"  Attempt {i+1} SQL: {sql}")
```

### ConversationResponse

Extends QueryResponse with conversation-specific information.

**Additional Fields**:

- `turn_number: int` - Which turn in the conversation
- `expanded_query: str` - Query after reference expansion
- `context_used: str` - Conversation context that was included
- `previous_results_referenced: bool` - Whether previous results were used

---

## Multi-turn Interface: ConversationManager

Manages conversation state and context across multiple queries.

### query()

```
query(user_input: str) -> ConversationResponse
```

Ask a question within the conversation context.

**Parameters**:
- `user_input`: User's natural language input

**Returns**: ConversationResponse with conversation metadata

**Raises**:
- `QueryExecutionError` if query fails
- `OpenAIError` if API call fails

**Example**:
```
conversation = engine.start_conversation()
r1 = conversation.query("Show me sales by region")
print(f"Turn 1: {r1.answer}")

r2 = conversation.query("Which region had the highest sales?")
print(f"Turn 2 (expanded from pronouns): {r2.expanded_query}")
print(f"Turn 2: {r2.answer}")
```

### get_history()

```
get_history() -> List[ConversationTurn]
```

Get all previous turns in the conversation.

**Returns**: List of ConversationTurn objects in order

**Example**:
```
history = conversation.get_history()
for turn in history:
    print(f"Turn {turn.turn_number}: {turn.user_input}")
    print(f"  Answer: {turn.answer}")
```

### get_context()

```
get_context() -> str
```

Get the synthesized conversation context (what will be passed to next query).

**Returns**: Context string (potentially truncated for token limits)

### clear()

```
clear() -> None
```

Reset conversation state, clearing all history.

**Example**:
```
conversation.clear()  # Start fresh conversation
```

### get_last_results()

```
get_last_results() -> Optional[List[Dict]]
```

Get the results from the most recent query (useful for debugging).

**Returns**: List of dicts, or None if no queries executed yet

---

## Error Handling

### Exception Hierarchy

```
QueryEngineError (base exception)
├─ ConfigurationError          # Config is missing/invalid
├─ DataSourceError             # Problem loading/accessing data
│  ├─ FileNotFoundError
│  ├─ DataFormatError
│  └─ SchemaError
├─ QueryExecutionError         # Problem executing query
│  ├─ SQLSyntaxError
│  ├─ SQLSchemaError
│  ├─ SQLSafetyError
│  ├─ QueryTimeoutError
│  └─ DebugFailedError
├─ APIError                    # OpenAI API issues
│  ├─ APIAuthenticationError
│  ├─ APIRateLimitError
│  ├─ APIUnavailableError
│  └─ APIParsingError
└─ ConversationError           # Multi-turn issues
   └─ AmbiguityResolutionError
```

### Error Handling Examples

```python
from nlqe import QueryEngine, QueryEngineConfig
from nlqe.errors import (
    QueryExecutionError,
    APIError,
    DebugFailedError
)

engine = QueryEngine(config)

try:
    response = engine.query("What was Q3 revenue?")
except DebugFailedError as e:
    # Query failed even after debug attempts
    print(f"Could not execute query: {e}")
    # Suggest user rephrase question
    
except APIError as e:
    # OpenAI API problem
    print(f"API error (retry later): {e}")
    
except QueryExecutionError as e:
    # DuckDB execution problem
    print(f"Query execution error: {e}")
    # Check datasource and schema
```

### Best Practices

- Always check `response.error` for failed queries
- Use `response.confidence_score` to decide if manual verification needed
- Log `response.generated_sql` for debugging
- For critical queries, use confidence threshold (e.g., only trust if >0.8)

---

## Evaluation Interface: Evaluator

Used for testing against golden datasets.

### run()

```
run() -> EvaluationMetrics
```

Run full evaluation against golden datasets.

**Returns**: EvaluationMetrics object with detailed results

**Example**:
```
evaluator = engine.create_evaluator("golden_datasets.yaml")
metrics = evaluator.run()

print(f"Accuracy: {metrics.accuracy:.1%}")
print(f"Passed: {metrics.passed_count}/{metrics.total_count}")
print(f"Avg Confidence: {metrics.avg_confidence:.2f}")
```

### run_single_test()

```
run_single_test(test_id: str) -> TestResult
```

Run a single test case for debugging.

**Parameters**:
- `test_id`: ID from golden dataset YAML

**Returns**: TestResult with detailed metrics for that test

**Example**:
```
result = evaluator.run_single_test("q3_revenue_total")
if not result.passed:
    print(f"Generated SQL: {result.generated_sql}")
    print(f"Expected SQL: {result.expected_sql}")
    print(f"Result Correctness: {result.result_correctness:.2f}")
    print(f"Answer Quality: {result.answer_quality:.2f}")
```

### EvaluationMetrics

Results from full evaluation run.

**Fields**:

- `accuracy: float` - Percentage of tests passed (both correctness and quality)
- `passed_count: int` - Number of tests passed
- `total_count: int` - Total number of tests
- `result_correctness_mean: float` - Average result correctness score
- `answer_quality_mean: float` - Average answer quality score
- `confidence_calibration_error: float` - RMS calibration error
- `avg_execution_time_ms: float` - Average query time
- `by_category: Dict[str, CategoryMetrics]` - Breakdown by query category
- `failures: List[FailureCase]` - Details of failed tests

**Example**:
```
metrics = evaluator.run()

print(f"Overall: {metrics.accuracy:.1%} passed")
print(f"Result Correctness: {metrics.result_correctness_mean:.2f}")
print(f"Answer Quality: {metrics.answer_quality_mean:.2f}")

for category, cat_metrics in metrics.by_category.items():
    print(f"{category}: {cat_metrics.accuracy:.1%}")
    
for failure in metrics.failures:
    print(f"FAILED: {failure.test_id} - {failure.reason}")
```

---

## DataSource Schema

Read-only information about loaded datasource.

### DataSourceSchema

```
DataSourceSchema:
  name: str
  description: str
  table_count: int
  tables: List[Table]
    Table:
      name: str
      description: str
      row_count: Optional[int]
      columns: List[Column]
        Column:
          name: str
          type: str
          nullable: bool
          description: Optional[str]
          example_values: List
```

**Example**:
```
schema = engine.get_schema()
print(f"Datasource: {schema.name}")
print(f"Tables: {schema.table_count}")

for table in schema.tables:
    print(f"\nTable: {table.name}")
    for col in table.columns:
        print(f"  {col.name}: {col.type}" + 
              (" (nullable)" if col.nullable else ""))
```

---

## Advanced Usage Patterns

### Custom Confidence Thresholds

```
# Only trust high-confidence answers
response = engine.query("What was revenue?")

if response.confidence_score > 0.85:
    # Trust the answer
    print(f"Confident answer: {response.answer}")
else:
    # Require manual verification
    print(f"Low confidence ({response.confidence_score:.0%})")
    print(f"Manual verification needed")
    print(f"SQL: {response.generated_sql}")
    print(f"Results: {response.data}")
```

### Batch Query Evaluation

```
# Evaluate multiple queries
questions = [
    "What was Q3 revenue?",
    "Which region had highest sales?",
    "How many active customers?",
]

for question in questions:
    response = engine.query(question)
    if response.error:
        print(f"ERROR: {question}")
    elif response.confidence_score < 0.7:
        print(f"LOW CONFIDENCE: {question}")
    else:
        print(f"OK: {question}")
```

### Conversation with Fallback

```
conversation = engine.start_conversation()

# If reference expansion fails, ask for clarification
response = conversation.query("Which one was best?")

if response.expanded_query == response.user_input:
    # No expansion happened - ambiguous
    print("Could you clarify which one you mean?")
else:
    # Expansion succeeded
    print(f"Understood: {response.expanded_query}")
    print(response.answer)
```

### Debugging Failed Queries

```
response = engine.query("Complex question about data")

if response.error:
    print(f"Query failed: {response.error}")
    print(f"Generated SQL: {response.generated_sql}")
    
    if response.debug_info:
        print(f"Tried {response.debug_info.attempts} fixes")
        print(f"First error: {response.debug_info.first_error}")
        print("Attempted SQLs:")
        for sql in response.debug_info.modified_sqls:
            print(f"  {sql}")
```

---

## Related Documentation

- [DESIGN.md](./DESIGN.md) - Design philosophy and goals
- [ARCHITECTURE.md](./ARCHITECTURE.md) - Internal implementation
- [TESTING.md](./TESTING.md) - Testing and evaluation
- [ROADMAP.md](./ROADMAP.md) - Implementation timeline
- [FAQ.md](./FAQ.md) - Design questions and decisions
