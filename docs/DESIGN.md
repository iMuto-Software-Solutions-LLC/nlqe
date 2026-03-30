# NLQE: Design Document

**Version**: v1.0.0  
**Last Updated**: March 17, 2026  
**Status**: POC Design Phase

## Executive Summary

This document outlines the design for a **Natural Language to SQL NLQE** that translates plain English questions into SQL queries executed against DuckDB datasources. The system uses OpenAI to generate and refine SQL queries, with built-in error recovery through an iterative debugging loop.

The design accommodates two phases:
1. **Proof of Concept** (Prototype Phase): Jupyter notebook demonstrating end-to-end flow
2. **Final Product**: Importable Python package with multi-turn conversation support, comprehensive testing framework, and production-ready error handling

### Key Design Goals

- **Accuracy**: >85% result correctness and >80% answer quality on golden datasets
- **Reliability**: Automatic query debugging with configurable retry logic
- **Usability**: Natural language interface with multi-turn conversation support
- **Testability**: Comprehensive evaluation framework with measurable accuracy metrics
- **Extensibility**: Designed as a library that can be imported and integrated into other products

---

## Problem Statement & Goals

### The Problem

Data insights often require SQL expertise. Business users, analysts, and even engineers frequently struggle to translate questions about data into SQL queries. This creates a bottleneck: either data teams must serve as interpreters, or valuable questions go unanswered.

### The Solution

By combining:
- **Large Language Models** (OpenAI) for SQL generation from natural language
- **DuckDB** for flexible query execution against structured data
- **Iterative Debugging** to recover from generated SQL errors
- **Multi-turn Conversation** to maintain context across related questions

We create a system where users can ask questions in plain English and get accurate data-driven answers without SQL knowledge.

### Design Goals

1. **Accuracy & Correctness**: Results must match expected output exactly (for measurable queries)
2. **Reliability**: System should recover from common SQL generation errors automatically
3. **Multi-turn Context**: Users should be able to ask follow-up questions with implicit context
4. **Transparency**: Users should understand what SQL was generated and have visibility into reasoning
5. **Measurable Quality**: System must include metrics to measure accuracy and confidence
6. **Production Ready**: Designed as reusable library, not one-off script

---

## Architecture Overview

### High-Level Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    User Query (Natural Language)             │
│              "What was revenue in Q3 by region?"             │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
        ┌────────────────────────────────────────┐
        │  1. Build Query Context                │
        │  - Load datasource schema              │
        │  - Select relevant examples            │
        │  - Add conversation history (if any)   │
        └─────────┬──────────────────────────────┘
                  │
                  ▼
        ┌────────────────────────────────────────┐
        │  2. Generate SQL via OpenAI            │
        │  - Call with context + user question   │
        │  - Extract SQL from response           │
        │  - Temperature=0 (deterministic)       │
        └─────────┬──────────────────────────────┘
                  │
                  ▼ Generated SQL
        ┌────────────────────────────────────────┐
        │  3. Execute Query in DuckDB            │
        │  - Validate syntax                     │
        │  - Execute with timeout                │
        │  - Capture results or error            │
        └─────────┬──────────────────────────────┘
                  │
         ┌────────┴─────────────────────────┐
         │                                   │
       ✓ Success                        ✗ Error
         │                                   │
         │                    ┌──────────────▼──────────────┐
         │                    │  4. Debug Loop (Max 3x)    │
         │                    │  - Call OpenAI with error   │
         │                    │  - Modify SQL based on tips │
         │                    │  - Retry execution          │
         │                    └──────────────┬──────────────┘
         │                                   │
         │                        ┌──────────┴─────────┐
         │                        │                    │
         │                      ✓ Success         ✗ Fail (3x)
         │                        │                    │
         │                        │        Return error to user
         │                        │
         └────────────┬───────────┘
                      │
                      ▼
        ┌────────────────────────────────────────┐
        │  5. Synthesize Natural Language Answer │
        │  - Call OpenAI to convert results      │
        │  - Generate readable summary           │
        │  - Calculate confidence score          │
        └─────────┬──────────────────────────────┘
                  │
                  ▼
        ┌────────────────────────────────────────┐
        │         Return QueryResponse           │
        │  - Generated SQL                       │
        │  - Query results (data)                │
        │  - Natural language answer             │
        │  - Confidence score                    │
        │  - Debug info (if applicable)          │
        └────────────────────────────────────────┘
```

### Core Components

| Component | Responsibility | Key Concerns |
|-----------|-----------------|--------------|
| **Query Context Builder** | Assemble datasource schema, descriptions, and relevant examples into a prompt context | Schema completeness, example relevance |
| **OpenAI Integration** | Generate and refine SQL queries via API calls | API cost, latency, response parsing |
| **DuckDB Executor** | Execute SQL safely with timeout and error capture | SQL injection prevention, resource limits |
| **Debug Loop** | Iteratively fix failed queries with AI assistance | Max attempts, cost accumulation |
| **Answer Synthesizer** | Convert raw query results to natural language | Factual accuracy, readability |
| **Conversation Manager** | Maintain multi-turn context and expand ambiguous references | Context window limits, history tracking |

---

## Prototype Phase (POC)

### Objectives

The prototype establishes a **proof of concept** for the complete flow:

- Validate that OpenAI can reliably generate SQL from natural language
- Test DuckDB integration patterns
- Verify the debug loop can recover from common SQL errors
- Demonstrate multi-turn conversation with context preservation
- Identify gaps and refinement areas before full product development

### Prototype Scope

**Format**: Jupyter notebook (`prototype.ipynb`)

**Contents**:

1. **Setup Section**
   - Import libraries (duckdb, openai, pydantic)
   - Load environment variables (API keys)
   - Initialize mock datasource

2. **Datasource Introspection Section**
   - Display schema of available tables/columns
   - Show datasource description and metadata
   - Show example Q&A patterns relevant to the dataset

3. **Query Flow Section**
   - Implement and demonstrate the full 5-step query pipeline
   - Show SQL generation
   - Show query execution
   - Show debugging if needed
   - Show answer synthesis

4. **Experimentation Section**
   - Test multiple user queries (5-10 different patterns)
   - Log success/failure for each
   - Document any issues discovered
   - Measure OpenAI API calls per query

5. **Findings & Insights**
   - Summary of what worked well
   - Issues encountered
   - Refinements needed before production

### Prototype Dependencies

Add to `pyproject.toml`:

```
pydantic-settings>=2.0.0    # Environment variable management
openai>=1.0.0              # OpenAI API client
python-dotenv>=1.0.0       # Load .env files
```

### Prototype Deliverables

1. **prototype.ipynb** - Complete POC notebook with all 5 sections
2. **Mock datasource files** - Example parquet/CSV for testing (sales data recommended)
3. **Sample queries & golden answers** - 5-10 test cases with expected results
4. **.env.example** - Template for required API keys
5. **Findings document** - Summary of learnings for handoff to Phase 2

---

## Final Product Architecture

### Package Structure

```
nlqe/
├── src/nlqe/
│   ├── __init__.py                 # Public API exports
│   ├── config.py                   # Configuration models
│   ├── types.py                    # Type definitions
│   │
│   ├── datasource/
│   │   ├── __init__.py
│   │   ├── introspector.py         # Schema discovery
│   │   ├── manager.py              # Datasource lifecycle
│   │   └── types.py                # Datasource models
│   │
│   ├── openai/
│   │   ├── __init__.py
│   │   ├── client.py               # OpenAI API wrapper
│   │   ├── prompts.py              # Prompt templates
│   │   ├── models.py               # Request/response models
│   │   └── validation.py           # Response validation
│   │
│   ├── duckdb/
│   │   ├── __init__.py
│   │   ├── executor.py             # Query execution engine
│   │   ├── safety.py               # SQL injection prevention
│   │   └── utils.py                # DuckDB utilities
│   │
│   ├── query/
│   │   ├── __init__.py
│   │   ├── loop.py                 # Query generation and debugging
│   │   ├── validator.py            # Result validation
│   │   └── cache.py                # Query result caching
│   │
│   ├── conversation/
│   │   ├── __init__.py
│   │   ├── manager.py              # Multi-turn context
│   │   ├── history.py              # Conversation history
│   │   └── models.py               # Conversation models
│   │
│   ├── synthesis/
│   │   ├── __init__.py
│   │   ├── answer.py               # Natural language synthesis
│   │   └── formatters.py           # Output formatting
│   │
│   ├── testing/
│   │   ├── __init__.py
│   │   ├── evaluator.py            # Accuracy evaluation
│   │   ├── metrics.py              # Metric calculations
│   │   └── datasets.py             # Golden dataset handling
│   │
│   └── utils/
│       ├── __init__.py
│       ├── logging.py
│       ├── errors.py               # Custom exceptions
│       └── constants.py
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py                 # pytest fixtures
│   ├── unit/
│   ├── integration/
│   └── fixtures/                   # Sample data and golden datasets
│
├── docs/                           # This documentation
├── config/
│   ├── default.yaml                # Default configuration
│   └── example.env                 # Environment template
│
└── README.md
```

### Key Interfaces

**QueryEngine (Main Entry Point)**

The primary interface users interact with:

- `__init__(config)` - Initialize with configuration
- `load_datasource(path)` - Load data source (parquet, CSV, or connection)
- `query(question)` - Execute single query, returns QueryResponse
- `start_conversation()` - Begin multi-turn conversation, returns ConversationManager
- `create_evaluator(golden_dataset)` - Create evaluation context, returns Evaluator

**QueryResponse (Output Model)**

Returned from each query:

- `user_query: str` - Original user question
- `generated_sql: str` - SQL that was executed
- `data: List[Dict]` - Raw query results
- `answer: str` - Natural language synthesis of results
- `confidence_score: float` - Confidence estimate (0.0-1.0)
- `execution_time_ms: float` - Query execution time
- `debug_info: Optional[DebugInfo]` - Information if query required debugging
- `error: Optional[str]` - Error message if query ultimately failed

**ConversationManager (Multi-turn Interface)**

For maintaining context across multiple queries:

- `query(question)` - Ask question in context of conversation history
- `get_history()` - Access all previous turns
- `clear()` - Reset conversation
- `get_context()` - Access synthesized conversation context

---

## Query Loop Detail

### Step 1: Build Query Context

Assemble all information needed for SQL generation:

1. **Datasource Schema**: Table and column definitions with types and descriptions
2. **Datasource Description**: High-level description of what data is available
3. **Example Patterns**: 5-10 relevant example Q&A pairs showing common query patterns
4. **Conversation History** (if multi-turn): Previous turns in current conversation
5. **Current Question**: The user's natural language question

This context is assembled into a structured prompt for OpenAI.

### Step 2: Generate SQL

Call OpenAI API with:
- System prompt defining the task and constraints
- Context (datasource info, examples, conversation history)
- User query
- `temperature=0` for deterministic results

Extract SQL from response and validate basic syntax.

### Step 3: Execute Query

- Validate SQL against schema (no references to non-existent tables/columns)
- Check for dangerous operations (DELETE, DROP, CREATE, etc.)
- Execute in DuckDB with configurable timeout (default 30s)
- Return results or capture error

### Step 4: Debug Loop (if needed)

If query fails:

1. Call OpenAI again with:
   - Original question
   - Failed SQL
   - Error message from DuckDB
   - Previous debug attempts (if any)

2. Apply suggested modifications to SQL

3. Retry execution

4. Repeat up to 3 times total (configurable)

5. If all attempts fail, prepare error summary for user

### Step 5: Synthesize Answer

Call OpenAI to convert query results into natural language:

1. Pass results and original question
2. Request conversational, clear summary
3. Extract generated text
4. Calculate confidence score based on multiple factors
5. Return complete QueryResponse

---

## Context Management

### Datasource Context

Static information about available data, loaded once at startup:

- Table names, column names, types
- Table and column descriptions
- Data ranges and statistics (for context)
- Example Q&A patterns relevant to this datasource
- Any special considerations (data freshness, join keys, etc.)

### Conversation Context

Dynamic information that grows with each query in a conversation:

- Previous user questions (exact wording)
- Generated SQL for each (for reference)
- Query results summary
- System's answers to previous questions
- Any ambiguities or clarifications made

Used to:
- Expand pronouns ("Which one?" → expand based on previous result)
- Provide historical context for follow-up questions
- Help understand what data the user has already seen

---

## Multi-Turn Conversation Support

### Conversation Flow

1. User starts conversation: `engine.start_conversation()`
2. User asks question: `conversation.query("What was Q3 revenue?")`
3. System responds with answer + results
4. User asks follow-up: `conversation.query("Which region?")`
5. System expands implicit references and answers with context
6. Repeat for multiple turns

### Reference Expansion

When user says "Which one had the highest?" the system must:

1. Recognize ambiguous reference
2. Look at previous results
3. Expand to full question: "Which region had the highest revenue?"
4. Generate SQL with complete context

### Benefits

- More natural conversation flow
- Users don't need to repeat context
- Follows typical user behavior with data analysis
- Reduces tokens needed (context is implicit, not explicit)

See [ARCHITECTURE.md](./ARCHITECTURE.md) for detailed implementation patterns.

---

## Configuration & Environment

### Configuration Model

Core settings for QueryEngine operation:

**OpenAI Settings**:
- `openai_api_key` - Required for API calls
- `openai_model` - Model to use (default: gpt-4)
- `openai_temperature` - Temperature for SQL generation (default: 0.0)
- `openai_max_tokens` - Max tokens per response (default: 2000)

**Query Execution Settings**:
- `query_timeout_seconds` - Timeout for DuckDB queries (default: 30)
- `max_debug_attempts` - Max times to retry failed queries (default: 3)

**Datasource Settings**:
- `datasource_path` - Path to parquet/CSV or connection string
- `datasource_type` - Type: "parquet", "csv", "duckdb", or "connection"

**Operational Settings**:
- `log_level` - Logging verbosity (default: INFO)
- `log_queries` - Whether to log all queries (default: true)

Load from environment variables with `NLQE_` prefix, or from `.env` file.

---

## Error Handling & Safety

### SQL Safety

Before executing any generated SQL:

1. **Syntax Validation**: Ensure SQL is valid DuckDB syntax
2. **Schema Validation**: Verify all tables/columns exist
3. **Dangerous Operation Detection**: Block operations like DROP, DELETE, INSERT, etc.
4. **Single Statement**: Ensure only one statement per query (prevent injection)

### Error Types

Different errors are handled differently:

- **SQL Syntax Error**: Pass to debug loop (AI can usually fix)
- **Schema Error** (table/column not found): Pass to debug loop
- **Execution Error** (timeout, memory): Fail immediately (unlikely to be fixable)
- **API Error** (OpenAI unavailable): Fail with clear message
- **Debug Failed** (3 attempts failed): Return detailed error summary to user

### Error Reporting

When query ultimately fails:

- Report what question was asked
- Show generated SQL (even though it failed)
- Explain why it failed (error message)
- Suggest potential issues (ambiguous table names, missing columns, etc.)
- Never expose internal error details that could be confusing

---

## Key Design Decisions

### Why Temperature=0 for SQL Generation?

SQL generation should be **deterministic** and reproducible:
- Same input always produces same output
- Easier to debug (consistent failures)
- Better for testing and evaluation
- Prevents "random" query generation variations

For natural language synthesis (answer generation), we could use `temperature=0.5` for slight variation while maintaining accuracy.

### Why Max 3 Debug Attempts?

- **1 attempt**: Too strict, many legitimate errors won't be fixed
- **3 attempts**: Balances success rate (most fixable errors recover) vs. API cost
- **5+ attempts**: Diminishing returns, expensive, user has waited long enough
- **Configurable**: Advanced users can adjust if needed

### Why Multi-Turn as Core Feature (Not Optional)?

Real data analysis is inherently conversational:
- Users naturally ask follow-up questions
- Context carries significant meaning
- Implementing it later becomes a major refactor
- Building it in from the start makes design simpler

### Why Separate Synthesis Step?

Separating "get results" from "describe results":
- Cleaner separation of concerns
- Can optimize/customize each independently
- Different output formats become easy (table, narrative, JSON)
- Reusable for other query types

### Why DuckDB?

- In-process SQL engine (no server setup)
- Excellent columnar analytics performance
- Supports multiple data formats (parquet, CSV, etc.)
- Good DuckDB→pandas integration for further processing
- Active community and good documentation

---

## Next Steps & Success Criteria

### Prototype Success

- ✓ Notebook runs end-to-end without errors
- ✓ OpenAI generates valid SQL for test queries
- ✓ DuckDB executes generated SQL successfully
- ✓ Query results are accurate
- ✓ Natural language answers are readable
- ✓ Debug loop successfully recovers from 1-2 SQL errors
- ✓ Learnings documented for Phase 2

### Final Product Success

- ✓ >85% result correctness on golden datasets
- ✓ >80% answer quality rating
- ✓ Confidence scores are well-calibrated
- ✓ Multi-turn conversations work reliably
- ✓ <100ms average SQL generation time
- ✓ <5 second end-to-end for typical queries
- ✓ <2 OpenAI calls per query on average (after debug attempts)

---

## Related Documentation

- [ARCHITECTURE.md](./ARCHITECTURE.md) - Detailed component design and data flows
- [TESTING.md](./TESTING.md) - Testing strategy and accuracy metrics
- [API.md](./API.md) - Public API reference and usage patterns
- [ROADMAP.md](./ROADMAP.md) - Implementation timeline and phases
- [FAQ.md](./FAQ.md) - Design decisions and open questions
