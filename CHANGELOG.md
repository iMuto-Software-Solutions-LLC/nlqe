# Changelog

All notable changes to the Natural Language Query Engine (NLQE) will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-03-30

This is the initial open-source release of the **Natural Language Query Engine (NLQE)**. 

NLQE is a modular library designed to bridge the gap between human language and structured data. It leverages Large Language Models (LLMs) to automatically generate, validate, and execute SQL queries over in-process datasources.

### Added
- **Core Engine API**: Programmatic `QueryEngine` for executing natural language queries against arbitrary datasets.
- **Datasource Introspection**: Automatic schema discovery for locally stored `.csv` and `.parquet` files via DuckDB.
- **LLM Integrations**: 
  - First-class support for OpenAI's language models (`gpt-4o`, `gpt-3.5-turbo`, etc.).
  - Support for Anthropic's Claude (`claude-3-5-sonnet-20241022`, etc.) via `custom_llm_client`.
  - Extensible `LLMClient` class that wraps LangChain integrations.
- **DuckDB Execution Layer**: Secure, in-memory analytical query engine utilizing `duckdb>=1.5.0` to read `parquet` and `csv` files directly.
- **Iterative Debug Loop**: Automatic error recovery system. When DuckDB encounters a SQL syntax or schema mismatch error, the LLM is provided the error context to self-correct and re-execute the query (up to 3 attempts by default).
- **Multi-turn Conversations**: Context-aware `start_conversation()` feature enabling users to ask follow-up questions referencing previous tabular results natively.
- **Evaluation Framework**: `nlqe.testing.cli` evaluation system using "golden datasets" to securely score LLM generation accuracy, completeness, and confidence calibration.
- **Safety Checks**: Built-in AST-level checks mapping out dangerous queries (e.g. `DROP`, `DELETE`, `TRUNCATE`) prior to database execution.

### Security
- Verified protection against SQL injection attacks targeting the local process.
- Strictly uncoupled architecture to ensure API keys are injected at runtime exclusively via environment variables (`NLQE_OPENAI_API_KEY`) or securely initiated configurations.

### Performance
- Fully decoupled in-process querying resulting in sub-500ms analytical execution overhead.
- Configurable timeouts limiting run-away query consumption.