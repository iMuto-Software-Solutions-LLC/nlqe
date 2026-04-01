# NLQE (Natural Language NLQE)

A natural language to SQL query engine powered by [LangChain](https://python.langchain.com/) and DuckDB. Ask questions about your data in plain English — works with OpenAI, Anthropic, or any LangChain-compatible model.

**Version**: v0.1.0 | **Python**: 3.11+ | **License**: MIT

---

## Examples

### Single query

```python
from nlqe import QueryEngine, QueryEngineConfig

# Reads NLQE_OPENAI_API_KEY from environment or .env
config = QueryEngineConfig()
engine = QueryEngine(config)
engine.load_datasource("transactions.parquet")

response = engine.query("What was total revenue by region last month?")
print(response.answer)
# "North America led with $1.2M, followed by Europe at $890K ..."

print(f"SQL: {response.generated_sql}")
print(f"Rows: {len(response.data)}  Confidence: {response.confidence_score:.0%}")
```

### Querying External Databases (PostgreSQL, MySQL, MSSQL)

```python
from nlqe import QueryEngine, QueryEngineConfig
from nlqe.types import PostgresConfig

# Reads NLQE_POSTGRES_URI from environment
db_config = PostgresConfig() 

engine = QueryEngine(QueryEngineConfig())

# Introspect only the specified tables to save LLM context
engine.load_datasource(db_config, allowlist=["users", "orders"])

response = engine.query("How many active users placed an order last week?")
print(response.generated_sql)
# SELECT COUNT(DISTINCT u.id) FROM ext_db.users u JOIN ext_db.orders o ON ...
```

### Querying Remote Files (S3, HTTP, Azure)

```python
from nlqe import QueryEngine, QueryEngineConfig

# Configure S3 credentials (if using S3)
import os
os.environ["AWS_ACCESS_KEY_ID"] = "your_key"
os.environ["AWS_SECRET_ACCESS_KEY"] = "your_secret"
os.environ["AWS_REGION"] = "us-east-1"

engine = QueryEngine(QueryEngineConfig())

# Query directly from an S3 bucket
engine.load_datasource("s3://my-bucket/data/sales.parquet")

# Or from a public URL
# engine.load_datasource("https://example.com/data.csv")

response = engine.query("What are the total sales by category?")
print(response.answer)
```

### Multi-turn conversation

```python
conv = engine.start_conversation()

r1 = conv.query("Show me the top 5 products by revenue")
r2 = conv.query("Which of those had the highest return rate?")  # uses context from r1
r3 = conv.query("Compare that to last month")

print(r3.answer)
```

### Switch to LLM Providers

```python
from langchain_anthropic import ChatAnthropic
from nlqe import QueryEngine, QueryEngineConfig
from nlqe.llm import LLMClient

# Anthropic
llm = ChatAnthropic(model="claude-3-5-sonnet-20241022")
engine = QueryEngine(QueryEngineConfig(), custom_llm_client=LLMClient(llm))

# Ollama (Local)
from langchain_ollama import ChatOllama
engine = QueryEngine(QueryEngineConfig(), custom_llm_client=LLMClient(ChatOllama(model="llama3")))
```

---

## Installation

```bash
# Install core package
pip install pynlqe

# Install with development tools
pip install "pynlqe[dev]"
```

Generate the sample dataset for testing:

```bash
python create_sample_data.py
```

## Configuration

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

```ini
NLQE_LLM_PROVIDER=openai
NLQE_OPENAI_API_KEY=sk-...
NLQE_LLM_MODEL=gpt-4o
```

---

## Overview

NLQE translates plain English into SQL executed against structured data (Parquet, CSV) via DuckDB. It uses an iterative debug loop to automatically recover from SQL errors.

**Key features:**

- Swappable LLM providers (OpenAI, Anthropic, Ollama, etc.)
- Multi-turn conversations with context preservation
- Automatic SQL error recovery (Iterative Debug Loop)
- Robust evaluation framework with "golden datasets"
- High test coverage and strict type safety

---

## Architecture Overview

| Component | Location | Purpose |
|---|---|---|
| `QueryEngine` | `engine.py` | Main entry point |
| `LLMClient` | `llm/client.py` | SQL generation, debugging, and synthesis |
| `DuckDBExecutor` | `duckdb/executor.py` | Safe SQL execution via DuckDB |
| `QueryLoop` | `query/loop.py` | Orchestration logic |
| `ConversationManager` | `conversation/manager.py` | Multi-turn history tracking |

For more details see [ARCHITECTURE.md](./docs/ARCHITECTURE.md).

---

## Development

Use the provided `Makefile` for common development tasks:

```bash
make install    # Install dependencies
make lint       # Run ruff and mypy
make format     # Format code with ruff
make test       # Run all tests
make build      # Build distribution packages
```

### Running the Evaluation Suite

Evaluate the engine against standardized test cases:

```bash
python -m nlqe.testing.cli evaluate --dataset fixtures/golden_datasets.yaml
```

---

## Documentation

| Document | Description |
|----------|-------------|
| **[API.md](./docs/API.md)** | Public API reference and detailed usage |
| **[ARCHITECTURE.md](./docs/ARCHITECTURE.md)** | Technical design and component data flows |
| **[DESIGN.md](./docs/DESIGN.md)** | High-level goals and philosophy |
| **[TESTING.md](./docs/TESTING.md)** | Evaluation strategy and accuracy metrics |
| **[FAQ.md](./docs/FAQ.md)** | Design decisions and common questions |

---

## Future Roadmap

- **v0.2.0**: Support for PostgreSQL and Snowflake datasources, result caching, and custom synthesizers.
- **v1.0.0**: Cloud-native API, fine-tuning support, and advanced production monitoring.

---

## License

This project is licensed under the MIT License.
