"""Configuration management for NLQE."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class QueryEngineConfig(BaseSettings):
    """Main configuration for QueryEngine.

    All fields can be set via environment variables with the prefix
    ``NLQE_`` (case-insensitive), or via a ``.env`` file.

    Provider selection
    ------------------
    Set ``llm_provider`` to ``"openai"`` (default) or ``"anthropic"``.
    Supply the matching API key field; the other can be omitted.

    Example ``.env`` for OpenAI::

        NLQE_LLM_PROVIDER=openai
        NLQE_OPENAI_API_KEY=sk-...
        NLQE_LLM_MODEL=gpt-4o

    Example ``.env`` for Anthropic::

        NLQE_LLM_PROVIDER=anthropic
        NLQE_ANTHROPIC_API_KEY=sk-ant-...
        NLQE_LLM_MODEL=claude-3-5-sonnet-20241022
    """

    # ------------------------------------------------------------------
    # Provider selection
    # ------------------------------------------------------------------
    llm_provider: str = "openai"
    """LLM provider: ``"openai"`` or ``"anthropic"``."""

    llm_model: str = "gpt-4o"
    """Model name passed to the provider (e.g. ``gpt-4o``, ``claude-3-5-sonnet-20241022``)."""

    llm_temperature: float = 0.0
    """Generation temperature (0 = deterministic)."""

    llm_max_tokens: int = 2000
    """Maximum completion tokens per LLM call."""

    # ------------------------------------------------------------------
    # Provider API keys (only the active one needs to be set)
    # ------------------------------------------------------------------
    openai_api_key: str = ""
    """OpenAI API key — required when ``llm_provider="openai"``."""

    anthropic_api_key: str = ""
    """Anthropic API key — required when ``llm_provider="anthropic"``."""

    # ------------------------------------------------------------------
    # Query execution
    # ------------------------------------------------------------------
    query_timeout_seconds: int = 30
    max_debug_attempts: int = 3

    # ------------------------------------------------------------------
    # Datasource
    # ------------------------------------------------------------------
    datasource_path: str | None = None
    datasource_type: str | None = None

    # ------------------------------------------------------------------
    # Few-shot examples
    # ------------------------------------------------------------------
    few_shot_examples_path: str | None = None
    """Path to ``example_queries.yaml`` for few-shot SQL prompts.  Optional."""

    # ------------------------------------------------------------------
    # Operational
    # ------------------------------------------------------------------
    log_level: str = "INFO"
    log_queries: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="NLQE_",
        case_sensitive=False,
        extra="ignore",
    )
