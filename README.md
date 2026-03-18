# Query Engine

A natural language to SQL query engine powered by [LangChain](https://python.langchain.com/) and DuckDB. Ask questions about your data in plain English — works with OpenAI, Anthropic, or any LangChain-compatible model.

**Version**: v0.1.0 | **Python**: 3.11+ | **Status**: active development

---

## Examples

### Single query

```python
from query_engine import QueryEngine, QueryEngineConfig

# Reads QUERY_ENGINE_OPENAI_API_KEY from environment or .env
config = QueryEngineConfig()
engine = QueryEngine(config)
engine.load_datasource("sales.parquet")

response = engine.query("What was total revenue by region last quarter?")
print(response.answer)
# "North America led with $1.2M, followed by Europe at $890K ..."

print(f"SQL: {response.generated_sql}")
print(f"Rows: {response.result_rows}  Confidence: {response.confidence_score:.0%}")
```

### Multi-turn conversation

```python
conv = engine.start_conversation()

r1 = conv.query("Show me the top 5 products by revenue")
r2 = conv.query("Which of those had the highest return rate?")  # uses context from r1
r3 = conv.query("Compare that to last month")

print(r3.answer)
```

### Switch to Anthropic (or any provider)

```python
from langchain_anthropic import ChatAnthropic
from query_engine import QueryEngine, QueryEngineConfig
from query_engine.llm import LLMClient

llm = ChatAnthropic(model="claude-3-5-sonnet-20241022", api_key="sk-ant-...")
engine = QueryEngine(QueryEngineConfig(), custom_llm_client=LLMClient(llm))
engine.load_datasource("sales.parquet")

response = engine.query("What are the top 10 customers by lifetime value?")
```

### Use Ollama (local, no API key)

```python
from langchain_ollama import ChatOllama
from query_engine.llm import LLMClient

engine = QueryEngine(QueryEngineConfig(), custom_llm_client=LLMClient(ChatOllama(model="llama3")))
engine.load_datasource("sales.parquet")
```

### Enable few-shot examples for better SQL accuracy

```python
config = QueryEngineConfig(
    few_shot_examples_path="fixtures/example_queries.yaml"
)
engine = QueryEngine(config)
engine.load_datasource("sales.parquet")
```

### Inspect results directly

```python
response = engine.query("How many transactions per category?")

for row in response.data:
    print(row)
# {'category': 'Electronics', 'n': 712}
# {'category': 'Clothing', 'n': 601}
# ...
```

### Context manager (auto-close)

```python
with QueryEngine(config) as engine:
    engine.load_datasource("sales.parquet")
    print(engine.query("Average order value?").answer)
```

---

## Installation

```bash
pip install -e .

# With dev tools (pytest, ruff, mypy)
pip install -e ".[dev]"
```

Generate the sample dataset used in tests and notebooks:

```bash
python create_sample_data.py
```

## Configuration

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

```ini
# .env — OpenAI (default)
QUERY_ENGINE_LLM_PROVIDER=openai
QUERY_ENGINE_OPENAI_API_KEY=sk-...
QUERY_ENGINE_LLM_MODEL=gpt-4o

# .env — Anthropic
# QUERY_ENGINE_LLM_PROVIDER=anthropic
# QUERY_ENGINE_ANTHROPIC_API_KEY=sk-ant-...
# QUERY_ENGINE_LLM_MODEL=claude-3-5-sonnet-20241022

# Optional: inject few-shot SQL examples into every prompt
# QUERY_ENGINE_FEW_SHOT_EXAMPLES_PATH=fixtures/example_queries.yaml
```

All settings can also be passed directly to `QueryEngineConfig(...)`.

---

## Overview

Query Engine translates plain English into SQL executed against structured data (Parquet, CSV). It uses LangChain LCEL chains so the underlying model is fully swappable.

**Pipeline per query:**

```
User question
  → Build context  (schema + optional few-shot examples)
  → Generate SQL   (LLM via LangChain)
  → Execute SQL    (DuckDB)
  → [on failure]   Debug loop — LLM fixes the SQL (up to 3 attempts)
  → Synthesise     (LLM converts results to plain-English answer)
  → Return QueryResponse (SQL, data, answer, confidence score)
```

**Key features:**

- Works with any LangChain `BaseChatModel` — OpenAI, Anthropic, Ollama, Azure, etc.
- Multi-turn conversations with sliding-window message history
- Automatic SQL error recovery (iterative debug loop)
- Confidence scoring from multiple signals
- Golden-dataset evaluation framework with JSON/CSV/Markdown reports
- 109 tests, 68% coverage, ruff-clean

---

## Project Status

```
Phase 1 — Prototype          ✅ complete
Phase 2 — Tests & packaging  ✅ complete  (109 tests, ruff clean)
Phase 3 — Evaluation         ✅ complete  (golden datasets, evaluator, CLI)
Phase 4 — Polish & release   🔄 in progress
```

---

## Architecture Overview

### Components

| Component | Location | Purpose |
|---|---|---|
| `QueryEngine` | `engine.py` | Main entry point |
| `LLMClient` | `llm/client.py` | LangChain LCEL chains — generate, debug, synthesise |
| `DuckDBExecutor` | `duckdb/executor.py` | Execute SQL safely with timeout + validation |
| `QueryLoop` | `query/loop.py` | Orchestrate generate → execute → debug |
| `ConversationManager` | `conversation/manager.py` | Multi-turn history via `ChatMessageHistory` |
| `Evaluator` | `testing/evaluator.py` | Run golden-dataset accuracy evaluation |
| `ReportGenerator` | `testing/reporter.py` | JSON / CSV / Markdown reports |

For more details see [ARCHITECTURE.md](./docs/ARCHITECTURE.md).

---

## Quick Start

```bash
# 1. Install
pip install -e ".[dev]"

# 2. Configure
cp .env.example .env   # add your API key

# 3. Generate sample data
python create_sample_data.py

# 4. Run notebooks
jupyter notebook prototype.ipynb
jupyter notebook prototype_advanced.ipynb
```

See [API.md](./docs/API.md) for the complete API reference.

---

## Documentation

Complete design and implementation documentation:

| Document | Purpose | Pages |
|----------|---------|-------|
| **[DESIGN.md](./docs/DESIGN.md)** | High-level design, goals, architecture | 22 |
| **[ARCHITECTURE.md](./docs/ARCHITECTURE.md)** | Component design, data models, flows | 25 |
| **[TESTING.md](./docs/TESTING.md)** | Testing strategy, accuracy metrics | 24 |
| **[API.md](./docs/API.md)** | Public API specification, examples | 20 |
| **[ROADMAP.md](./docs/ROADMAP.md)** | Implementation timeline (6 weeks) | 22 |
| **[FAQ.md](./docs/FAQ.md)** | Design decisions, tradeoffs | 19 |
| **[IMPLEMENTATION_SUMMARY.md](./IMPLEMENTATION_SUMMARY.md)** | Phase 1 completion summary | 18 |
| **[EXAMPLE_QUERIES.md](./EXAMPLE_QUERIES.md)** | All 25+ example query patterns | 12 |
| **[fixtures/README.md](./fixtures/README.md)** | Sample data documentation | 8 |

---

## Key Design Decisions

See [FAQ.md](./docs/FAQ.md) for detailed rationale on:

- **Temperature=0 for SQL Generation**: Ensures deterministic, reproducible results
- **Max 3 Debug Attempts**: Balances recovery rate vs. API cost
- **Multi-turn as Core Feature**: Reflects real-world data analysis workflows
- **Separate Synthesis Step**: Clean separation between data retrieval and explanation
- **DuckDB as Executor**: In-process, flexible, no operational overhead
- **Confidence Scoring from Multiple Signals**: More robust than single metric

---

## Success Criteria

### Prototype Phase (This Week)
- ✓ Notebook runs end-to-end
- ✓ OpenAI generates reasonable SQL
- ✓ Debug loop recovers from errors
- ✓ Findings documented

### Final Product (Week 6)
- ✓ **>85% Result Correctness** on golden datasets
- ✓ **>80% Answer Quality** from LLM evaluation
- ✓ Multi-turn conversations work reliably
- ✓ <5 second average execution time
- ✓ Publicly released to PyPI

See [TESTING.md](./docs/TESTING.md) for detailed metrics.

---

## Project Structure

```
query-engine/
├── docs/                           # Complete design documentation
│   ├── DESIGN.md                   # High-level design
│   ├── ARCHITECTURE.md             # Technical details
│   ├── TESTING.md                  # Testing strategy
│   ├── API.md                      # Public API reference
│   ├── ROADMAP.md                  # Implementation timeline
│   └── FAQ.md                      # Design decisions & Q&A
├── src/
│   └── query_engine/               # Main package
├── tests/                          # 109 tests (unit + integration)
├── config/
│   └── example.env                 # Environment template
├── prototype.ipynb                 # POC notebook (will be built in Phase 1)
├── pyproject.toml                  # Project configuration
├── README.md                       # This file
└── .gitignore
```

---

## Development

### Prerequisites

- Python 3.11+
- OpenAI API key (get from https://platform.openai.com)
- Git (optional, for version control)

### Setup

```bash
# Clone or navigate to repository
cd query-engine

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install in development mode
pip install -e .

# Install dev dependencies (testing, formatting)
pip install -e ".[dev]"

# Configure
cp .env.example .env
# Edit .env with your OpenAI API key
```

### Generate Sample Data

```bash
python create_sample_data.py
```

This creates 4 parquet files in `fixtures/` directory:
- transactions.parquet (2,500 rows)
- customers.parquet (150 rows)
- regions.parquet (8 rows)
- products.parquet (25 rows)

### Code Quality

```bash
# Check code with ruff
ruff check src/

# Format code with ruff
ruff format src/

# Type checking (when mypy is added)
mypy src/
```

### Running Notebooks

```bash
# Start Jupyter
jupyter notebook

# Open in browser:
# - http://localhost:8888/notebooks/prototype.ipynb
# - http://localhost:8888/notebooks/prototype_advanced.ipynb
```

### Running Tests

```bash
pytest                        # Run all tests (109 tests)
pytest -v                     # Verbose output
pytest --cov                  # With coverage report
pytest tests/unit/            # Unit tests only
pytest tests/integration/     # Integration tests (real DuckDB, mock LLM)
pytest tests/integration/ --live  # End-to-end with real API (requires key)
```

### Building Package (Phase 4)

```bash
python -m build          # Create wheel and sdist
twine upload dist/*      # Upload to PyPI (after auth)
```

---

## Dependencies

### Core

- **langchain** >=0.3 — LCEL chains, prompt templates, message history
- **langchain-openai** — OpenAI provider
- **langchain-anthropic** — Anthropic provider
- **langchain-community** — In-memory chat history and community integrations
- **duckdb** >=1.5 — In-process SQL engine
- **pydantic** >=2.12 — Data models and validation
- **pydantic-settings** >=2.0 — Environment variable management
- **pyyaml** >=6.0 — YAML config parsing

### Development

- **pytest** + **pytest-cov** + **pytest-mock** — Testing
- **ruff** — Linting and formatting
- **mypy** — Type checking

---

## Design Goals

1. **Accuracy**: Generate SQL that returns correct results
2. **Reliability**: Recover from common SQL generation errors
3. **Usability**: Natural language interface, multi-turn support
4. **Testability**: Measurable accuracy and confidence
5. **Extensibility**: Reusable library, not a one-off script
6. **Transparency**: Users understand what SQL was generated

---

## Known Limitations (POC)

- Single datasource at a time (no cross-datasource joins yet)
- Limited to parquet/CSV (SQL databases future work)
- No fine-tuning on user data (uses base OpenAI model)
- No caching (every query hits API)
- No high availability (single process)

See [FAQ.md](./docs/FAQ.md) for more details on design tradeoffs.

---

## Roadmap

### v0.1.0 (Week 6)
- Core package with query generation and execution
- Multi-turn conversation support
- Golden dataset evaluation framework
- Public release to PyPI

### v0.2.0 (Future)
- Additional datasource types (PostgreSQL, Snowflake)
- Result caching
- Custom synthesizers
- Better confidence calibration

### v1.0.0 (Future)
- Cloud API
- Fine-tuning on custom data
- Advanced debugging
- Production monitoring

See [ROADMAP.md](./docs/ROADMAP.md) for detailed timeline.

---

## Contributing

Not yet accepting external contributions (POC phase). Once v0.1.0 is released, contributions will be welcome!

---

## License

MIT (to be confirmed)

---

## Questions & Feedback

This is a proof-of-concept project. All feedback is welcome!

- **Design Questions**: See [FAQ.md](./docs/FAQ.md)
- **Architecture**: See [ARCHITECTURE.md](./docs/ARCHITECTURE.md)
- **Implementation Details**: See [ROADMAP.md](./docs/ROADMAP.md)
- **API Usage**: See [API.md](./docs/API.md)

---

## Citation

If you use Query Engine in your research or product, please cite:

```
Query Engine: Natural Language to SQL via OpenAI and DuckDB
v0.1.0 (POC), March 2026
```

---

**Status**: 🚧 Under active development - design phase complete, implementation starting week 1.

See [DESIGN.md](./docs/DESIGN.md) for complete design overview.
