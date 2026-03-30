# NLQE: Architecture Document

**Version**: v1.0.0  
**Last Updated**: March 17, 2026  
**Status**: POC Architecture Design

## Overview

This document provides detailed technical architecture for the NLQE. It describes component interactions, data models, state management patterns, and integration points. See [DESIGN.md](./DESIGN.md) for high-level overview and design philosophy.

---

## Component Responsibilities

### Query Context Builder

**Purpose**: Assemble all contextual information needed for SQL generation

**Responsibilities**:
- Load datasource schema (tables, columns, types)
- Load datasource description and metadata
- Select relevant example Q&A patterns (e.g., top 5 most similar to current query)
- For multi-turn: include conversation history
- Format everything into a structured prompt string

**Inputs**:
- Datasource definition
- User query
- Optional: conversation history

**Outputs**:
- Formatted context string ready for OpenAI prompt
- Metadata about what examples were selected

**Key Concerns**:
- Context token limit (don't exceed OpenAI's 8K limit)
- Example relevance (selecting similar patterns improves generation quality)
- Schema completeness (missing columns lead to generation errors)

### OpenAI Integration Layer

**Purpose**: Communicate with OpenAI API for SQL generation and refinement

**Responsibilities**:
- Format requests to OpenAI API
- Handle authentication and API keys
- Call with appropriate parameters (model, temperature, max_tokens)
- Parse responses and extract SQL queries
- Handle rate limits and retries
- Log API calls for monitoring

**Interfaces**:
- `generate_sql(context, user_query)` → sql_string
- `debug_sql(context, failed_sql, error_message)` → refined_sql_string
- `synthesize_answer(query_results, user_query)` → natural_language_answer

**Key Concerns**:
- API cost (track tokens used)
- Latency (add observability)
- Response parsing (SQL might not be in expected format)
- Error handling (API failures, invalid responses)

### DuckDB Executor

**Purpose**: Execute SQL queries safely with error capture

**Responsibilities**:
- Establish and manage DuckDB connection(s)
- Validate SQL before execution (syntax, schema, safety)
- Execute queries with timeout protection
- Capture results or errors cleanly
- Support both single queries and multi-statement contexts
- Handle datasource registration (parquet files, CSV, connections)

**Interfaces**:
- `execute(sql_string)` → (success: bool, data: List[Dict] | error: str)
- `validate_sql(sql_string)` → (is_valid: bool, issues: List[str])
- `register_datasource(path, format)` → success: bool

**Key Concerns**:
- SQL injection prevention (validate all input)
- Resource limits (timeout, memory usage)
- Datasource freshness (cached vs. live data)
- Error messages (clear, actionable feedback)

### Debug Loop

**Purpose**: Iteratively fix failed queries through AI assistance

**Responsibilities**:
- Detect query failures
- Call OpenAI with context about the failure
- Apply suggested modifications
- Retry execution
- Track number of attempts
- Fail gracefully after max attempts

**State**:
- Current attempt number (1-3)
- Previous failed SQLs (for context)
- Previous error messages

**Termination Conditions**:
- Query succeeds → return results
- Max attempts exceeded → return error summary
- Unrecoverable error detected → fail immediately

**Key Concerns**:
- Cost accumulation (each retry costs API calls)
- User patience (don't retry forever)
- Error quality (are debug suggestions helpful?)
- Circular failures (avoid infinite retry loops)

### Answer Synthesizer

**Purpose**: Convert query results to natural language

**Responsibilities**:
- Take raw query results and original user question
- Call OpenAI to generate natural language summary
- Ensure answer is complete and accurate
- Calculate confidence score
- Support multiple output formats (narrative, bullet points, etc.)

**Inputs**:
- Query results (list of dicts)
- Original user question
- Query metadata (execution time, row count, etc.)

**Outputs**:
- Natural language answer string
- Confidence score (0.0-1.0)
- Metadata (answer length, key statistics, etc.)

**Key Concerns**:
- Factual accuracy (answer must match the data)
- Completeness (all important information included)
- Readability (clear, conversational tone)
- Confidence calibration (score reflects actual reliability)

### Conversation Manager

**Purpose**: Maintain context across multiple queries in a conversation

**Responsibilities**:
- Store conversation history
- Expand ambiguous references (pronouns, "that region", etc.)
- Build conversation context string
- Manage conversation state (active, archived)
- Provide history access for debugging

**State per Conversation**:
- Turn history (list of previous turns)
- Context window (synthesized context for next query)
- Participants (tracking which datasource/user)

**Turn Structure**:
- User question (original input)
- Expanded question (after reference resolution)
- Generated SQL
- Query results summary
- System answer

**Key Concerns**:
- Context window limits (conversation can't grow infinitely)
- Reference resolution (correctly identify what "that" refers to)
- Token efficiency (compress history over time)
- Ambiguity handling (when references can't be resolved)

---

## Detailed Query Loop Flow

```
INPUT: user_query, datasource, optional context

PHASE 1: CONTEXT ASSEMBLY
├─ Load datasource schema
├─ Load datasource description
├─ Select relevant examples (5-10 most similar to current query)
└─ If multi-turn: include conversation history
    └─ Output: context_string

PHASE 2: SQL GENERATION
├─ Call OpenAI with:
│  ├─ System prompt (define task, constraints)
│  ├─ Context string (schema, examples, history)
│  ├─ User query
│  └─ temperature=0 (deterministic)
├─ Parse response to extract SQL
└─ Output: generated_sql

PHASE 3: EXECUTION
├─ Validate SQL:
│  ├─ Check syntax (valid DuckDB)
│  ├─ Check schema (tables/columns exist)
│  └─ Block dangerous ops (DROP, DELETE, etc.)
├─ Execute in DuckDB with 30s timeout
└─ Branch on result:
    ├─ SUCCESS → go to PHASE 5
    └─ ERROR → go to PHASE 4

PHASE 4: DEBUG LOOP (max 3 iterations)
├─ FOR attempt in 1..3:
│  ├─ Call OpenAI with:
│  │  ├─ Original question
│  │  ├─ Failed SQL
│  │  ├─ DuckDB error message
│  │  └─ Previous attempts (context)
│  ├─ Extract suggested modifications
│  ├─ Apply to SQL
│  ├─ Validate modified SQL
│  ├─ Execute in DuckDB
│  └─ IF success → go to PHASE 5
│     ELSE → continue loop
├─ IF all attempts failed:
│  └─ Generate error summary
│     └─ Return error to user, STOP
└─ ELSE: go to PHASE 5

PHASE 5: ANSWER SYNTHESIS
├─ Call OpenAI with:
│  ├─ Query results
│  ├─ Original question
│  └─ Result metadata (row count, types, etc.)
├─ Generate natural language answer
├─ Calculate confidence score
└─ Output: answer_string, confidence_score

OUTPUT: QueryResponse
├─ user_query
├─ generated_sql
├─ data (raw results)
├─ answer
├─ confidence_score
├─ execution_time_ms
├─ debug_info (if applicable)
└─ error (if applicable)
```

---

## Data Models

### Datasource Definition

Information describing what data is available:

```
DataSource:
  name: string                    # "sales_database"
  description: string             # "Monthly sales with transactions, customers, regions"
  type: "parquet" | "csv" | "duckdb"
  path: string                    # "/data/sales.parquet"
  
  tables: List[Table]
    Table:
      name: string                # "transactions"
      description: string         # "Individual transaction records"
      columns: List[Column]
        Column:
          name: string            # "amount"
          type: string            # "DECIMAL(10,2)"
          description: string     # "Transaction amount in USD"
          nullable: bool
          example_values: List    # For context

  examples: List[Example]         # Example Q&A patterns
    Example:
      question: string            # "What was revenue in Q3?"
      sql: string                 # "SELECT SUM(amount) FROM transactions WHERE..."
      explanation: string         # Why this SQL pattern is useful
```

### Query Request

What the user provides:

```
QueryRequest:
  user_query: string              # "Show me Q3 revenue by region"
  context: Optional[string]       # Optional previous context
  conversation_id: Optional[str]  # For multi-turn tracking
```

### Query Response

What the system returns:

```
QueryResponse:
  user_query: string              # Original question
  generated_sql: string           # SQL that was executed
  data: List[Dict]                # Raw results (each row as dict)
  answer: string                  # Natural language answer
  confidence_score: float         # 0.0 to 1.0
  execution_time_ms: float        # Query execution time
  result_rows: int                # Number of rows returned
  
  debug_info: Optional[DebugInfo]
    DebugInfo:
      attempts: int               # Number of retries needed
      errors: List[str]           # Errors encountered
      modified_sqls: List[str]    # SQL variations tried
  
  error: Optional[str]            # Error message if failed
```

### Conversation Turn

One turn in a multi-turn conversation:

```
ConversationTurn:
  turn_number: int
  user_input: string              # Raw user input
  expanded_query: string          # After reference expansion
  generated_sql: string
  results_summary: string         # Brief summary of results
  answer: string
  timestamp: datetime
  execution_time_ms: float
```

### Conversation History

State for multi-turn conversation:

```
ConversationHistory:
  conversation_id: string
  datasource: DataSource
  created_at: datetime
  turns: List[ConversationTurn]
  context_window: string          # Compressed context for next turn
  last_query_results: List[Dict]  # Previous results (for reference resolution)
```

---

## Context Management

### Datasource Context Assembly

When building prompt context for SQL generation:

1. **Schema Section** (concise)
   ```
   Available Tables:
   - transactions (cols: id, date, amount, customer_id, region_id)
   - customers (cols: id, name, region_id, signup_date)
   - regions (cols: id, name, country)
   ```

2. **Description Section**
   ```
   Sales database contains monthly transaction data from 2020 onwards.
   - transactions: Individual sales records
   - customers: Customer master data
   - regions: Geographic region definitions
   ```

3. **Example Patterns Section**
   ```
   Q: What was Q3 revenue?
   A: SELECT SUM(amount) FROM transactions WHERE QUARTER(date) = 3
   
   Q: Revenue by region?
   A: SELECT regions.name, SUM(transactions.amount) FROM transactions
      JOIN regions ON transactions.region_id = regions.id
      GROUP BY regions.name ORDER BY SUM(transactions.amount) DESC
   ```

4. **Conversation History Section** (if multi-turn)
   ```
   Previous turn:
   Q: Show me Q3 revenue by region
   A: [Results showing regions and amounts]
   
   Previous turn:
   Q: Which region had highest?
   A: North America with $1.5M
   ```

### Token Limit Management

Context must fit within OpenAI's token limits. Strategy:

- Prioritize: Description > Most relevant examples > Full schema
- Compress: Summarize very long conversation histories
- If still too large: Select fewer examples, shorter descriptions

### Example Selection

Not all examples are equally useful. Smart selection:

- Calculate semantic similarity between user query and existing examples
- Select top 5 most similar examples
- If no good matches, select diverse examples covering different query types

---

## Multi-Turn Conversation Handling

### Reference Expansion

When user says "Which one?" or "That region", system must:

1. **Detect ambiguous reference** (pronouns, demonstratives)

2. **Look at previous results**
   - What columns were in previous result?
   - What entities were listed?

3. **Call OpenAI for expansion**
   - Input: ambiguous query, previous results
   - Output: expanded question with specific entity names
   - Example: "Which one?" → "Which region had the highest revenue?"

4. **Execute with expanded query**

### Context String Building

For each new query in conversation, build a context that includes:

```
Current Query: "Which region had the highest?"

Conversation Context:
- Earlier you asked about Q3 revenue
- I showed results with regions: North America ($1.5M), Europe ($1.2M), Asia ($0.8M)
- So "highest" likely refers to highest revenue amount
- "Region" is the entity we're comparing
```

### Ambiguity Handling

Sometimes references can't be resolved:

- Query: "How did that change?"
- Previous results: (no temporal data to compare)
- Action: Ask for clarification rather than guess

Error message: "I'm not sure what to compare. Could you specify which two time periods?"

---

## State Management Patterns

### QueryEngine State

**Per Instance**:
- Active datasource (loaded once, reused)
- Configuration (API keys, timeouts, etc.)
- Cached schema information

**Per Query**:
- Current context
- Current SQL
- Attempt counter
- Error history

### ConversationManager State

**Per Conversation**:
- Conversation ID
- All previous turns
- Context window (for next query)
- Last results (for reference resolution)

### DuckDB Connection State

**Pool Management**:
- One connection per datasource
- Reuse connection across queries (more efficient)
- Clean shutdown on manager destruction
- Handle connection timeouts gracefully

---

## Integration Points

### Datasource Integration

System must support:

1. **Parquet Files**
   - Register file with DuckDB
   - Load schema via DuckDB introspection
   - Support partitioned datasets

2. **CSV Files**
   - Parse CSV with appropriate options
   - Infer schema or use provided schema
   - Handle different delimiters/encodings

3. **DuckDB Native**
   - Direct DuckDB database connection
   - Introspect existing schema
   - Support multiple tables/views

4. **Future: SQL Databases**
   - PostgreSQL, MySQL, Snowflake, etc.
   - Via DuckDB's external data support

### OpenAI Integration

**API Patterns**:
- Async request handling for non-blocking calls
- Automatic retry on rate limits
- Token counting and monitoring
- Response validation and parsing

**Error Handling**:
- API unavailable → Clear error message
- Rate limited → Exponential backoff
- Invalid response → Parsing error
- Insufficient context → Truncate and retry

### Logging & Monitoring

**Logged Events**:
- Query request received
- SQL generated
- Query execution (time, rows)
- Debug attempts
- Answer synthesized
- Error conditions

**Metrics Tracked**:
- Total API calls per query
- Total execution time
- Success rate
- Average debug attempts
- Confidence score distribution

---

## Error Handling

### SQL Validation

Before execution, check:

1. **Syntax** - Is this valid DuckDB SQL?
2. **Schema** - Do all tables and columns exist?
3. **Safety** - No DROP, DELETE, INSERT, UPDATE, etc.
4. **Cardinality** - Not selecting 1M+ rows unnecessarily

### Error Classification

```
SQLSyntaxError
├─ Caused by: Invalid SQL format
├─ Handling: Pass to debug loop (AI often fixes)
└─ User message: "SQL was malformed, retrying..."

SchemaError
├─ Caused by: Table or column doesn't exist
├─ Handling: Pass to debug loop (AI can find right name)
└─ User message: "Column name wasn't found, searching alternatives..."

ExecutionError
├─ Caused by: Timeout, out of memory, query too complex
├─ Handling: Fail immediately (unlikely to be fixable)
└─ User message: "Query was too complex or took too long"

DebugFailedError
├─ Caused by: All 3 debug attempts failed
├─ Handling: Return detailed error summary
└─ User message: Specific guidance based on error pattern

ParsingError
├─ Caused by: Can't parse SQL from AI response
├─ Handling: Request clarification from AI
└─ User message: "Had trouble understanding AI response"
```

### Error Recovery Strategies

| Error Type | Strategy |
|-----------|----------|
| Table not found | Suggest similar table names, list available tables |
| Column not found | Suggest similar column names, show table structure |
| SQL syntax error | Explain the syntax rule violated |
| Timeout | Suggest filtering/limiting data |
| Type mismatch | Suggest casting or different operations |
| Ambiguous reference | Ask user to clarify |

---

## Data Flow Diagram

```
User
  │
  ├─→ QueryEngine.query(question)
  │        │
  │        ├─→ ContextBuilder.build_context(datasource, question)
  │        │        │
  │        │        └─→ outputs: context_string
  │        │
  │        ├─→ OpenAIClient.generate_sql(context, question)
  │        │        │
  │        │        └─→ outputs: generated_sql
  │        │
  │        ├─→ DuckDBExecutor.execute(sql)
  │        │        │
  │        │        ├─→ SUCCESS
  │        │        │        │
  │        │        │        └─→ outputs: result_list
  │        │        │
  │        │        └─→ ERROR
  │        │                 │
  │        │                 ├─→ DebugLoop.debug(question, sql, error)
  │        │                 │        │
  │        │                 │        ├─→ OpenAIClient.debug_sql(...)
  │        │                 │        │
  │        │                 │        ├─→ DuckDBExecutor.execute(modified_sql)
  │        │                 │        │
  │        │                 │        └─→ outputs: result_list or error
  │        │                 │
  │        │                 └─→ If max attempts exceeded
  │        │                         └─→ outputs: error_summary
  │        │
  │        ├─→ AnswerSynthesizer.synthesize(results, question)
  │        │        │
  │        │        ├─→ OpenAIClient.synthesize_answer(...)
  │        │        │
  │        │        └─→ outputs: answer, confidence_score
  │        │
  │        └─→ Return QueryResponse
  │
  └─← QueryResponse
       ├─ user_query
       ├─ generated_sql
       ├─ data
       ├─ answer
       ├─ confidence_score
       └─ debug_info (if applicable)
```

---

## Package Export Structure

**Public API** (what users import):

```
from nlqe import (
    QueryEngine,
    QueryResponse,
    ConversationManager,
    QueryEngineConfig,
)

from nlqe.testing import (
    Evaluator,
    EvaluationMetrics,
    GoldenDataset,
)
```

**Internal Modules** (not part of public API):

- `nlqe.openai.*` (internal integration)
- `nlqe.duckdb.*` (internal integration)
- `nlqe.query.*` (internal loop logic)
- `nlqe.utils.*` (internal utilities)

---

## Related Documentation

- [DESIGN.md](./DESIGN.md) - High-level design and philosophy
- [TESTING.md](./TESTING.md) - Testing strategy and metrics
- [API.md](./API.md) - Public API reference
- [ROADMAP.md](./ROADMAP.md) - Implementation timeline
- [FAQ.md](./FAQ.md) - Design decisions and open questions
