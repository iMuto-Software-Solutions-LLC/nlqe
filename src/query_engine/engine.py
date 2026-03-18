"""Main QueryEngine class."""

from query_engine.config import QueryEngineConfig
from query_engine.conversation.manager import ConversationManager
from query_engine.datasource.manager import DataSourceManager
from query_engine.duckdb.executor import DuckDBExecutor
from query_engine.llm.client import (
    LLMClient,
    anthropic_client,
    load_few_shot_examples,
    openai_client,
)
from query_engine.query.loop import QueryLoop
from query_engine.types import DataSourceSchema, QueryResponse
from query_engine.utils import ConfigurationError, get_logger, setup_logging

logger = get_logger(__name__)


class QueryEngine:
    """Main Query Engine class — primary user interface.

    Supports any LangChain-compatible LLM provider via ``QueryEngineConfig``.
    Set ``llm_provider`` to ``"openai"`` or ``"anthropic"`` and supply the
    matching API key.  To use a custom model (e.g. Ollama), construct an
    ``LLMClient`` manually and pass it via ``custom_llm_client``.

    Example (OpenAI)::

        config = QueryEngineConfig()          # reads from .env
        engine = QueryEngine(config)
        engine.load_datasource("data.parquet")
        response = engine.query("How many sales last month?")

    Example (custom model)::

        from langchain_ollama import ChatOllama
        from query_engine.llm.client import LLMClient

        llm = LLMClient(ChatOllama(model="llama3"))
        engine = QueryEngine(config, custom_llm_client=llm)
    """

    def __init__(
        self,
        config: QueryEngineConfig,
        custom_llm_client: LLMClient | None = None,
    ) -> None:
        """Initialise QueryEngine.

        Args:
            config: ``QueryEngineConfig`` (reads from env / .env by default).
            custom_llm_client: Optional pre-configured ``LLMClient``.  When
                provided, ``config.llm_provider`` / API-key fields are ignored
                for LLM construction.

        Raises:
            ConfigurationError: If the required API key is missing.
        """
        setup_logging(config.log_level)
        logger.info("Initialising QueryEngine")

        self.config = config
        self.datasource_manager = DataSourceManager()
        self.llm_client: LLMClient | None = custom_llm_client
        self.duckdb_executor: DuckDBExecutor | None = None
        self.query_loop: QueryLoop | None = None
        self.schema: DataSourceSchema | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_datasource(
        self,
        path: str,
        name: str | None = None,
        description: str | None = None,
        datasource_type: str | None = None,
    ) -> DataSourceSchema:
        """Load a datasource and initialise the query pipeline.

        Args:
            path: Path to the datasource file (parquet, CSV, DuckDB).
            name: Optional human-readable name.
            description: Optional description injected into the LLM prompt.
            datasource_type: Optional type hint (``"parquet"``, ``"csv"``,
                ``"duckdb"``).  Auto-detected from extension when omitted.

        Returns:
            ``DataSourceSchema`` describing the loaded tables.

        Raises:
            FileNotFoundError: If the file doesn't exist.
            SchemaError: If the format is not recognised.
            ConfigurationError: If the required provider API key is missing.
        """
        logger.info(f"Loading datasource: {path}")

        self.schema = self.datasource_manager.load_datasource(
            path,
            name=name,
            description=description,
            datasource_type=datasource_type,
        )

        # Build (or reuse) LLM client
        if self.llm_client is None:
            self.llm_client = self._build_llm_client()

        # Initialise DuckDB executor
        self.duckdb_executor = DuckDBExecutor(path)

        # Initialise query loop
        self.query_loop = QueryLoop(
            llm_client=self.llm_client,
            duckdb_executor=self.duckdb_executor,
            max_debug_attempts=self.config.max_debug_attempts,
        )

        logger.info(f"Datasource loaded: {self.schema.name}")
        return self.schema

    def query(self, user_query: str) -> QueryResponse:
        """Execute a single natural-language query.

        Args:
            user_query: Natural language question.

        Returns:
            ``QueryResponse`` with SQL, results, and synthesised answer.

        Raises:
            ValueError: If no datasource has been loaded.
            DebugFailedError: If the query fails after all debug attempts.
        """
        if not self.schema or not self.query_loop:
            raise ValueError("No datasource loaded. Call load_datasource() first.")

        logger.info(f"Executing query: {user_query!r}")

        context = self._build_context()
        response = self.query_loop.execute(
            user_query,
            context,
            query_timeout_seconds=self.config.query_timeout_seconds,
        )

        if self.config.log_queries:
            logger.info(f"SQL: {response.generated_sql}")
            logger.info(
                f"Rows: {response.result_rows}  Confidence: {response.confidence_score:.0%}"
            )

        return response

    def start_conversation(self) -> ConversationManager:
        """Start a new multi-turn conversation session.

        Returns:
            ``ConversationManager`` bound to this engine's datasource.

        Raises:
            ValueError: If no datasource has been loaded.
        """
        if not self.schema or not self.query_loop:
            raise ValueError("No datasource loaded. Call load_datasource() first.")

        logger.info("Starting new conversation")
        return ConversationManager(self.query_loop, self._build_context())

    def get_schema(self) -> DataSourceSchema | None:
        """Return the current datasource schema, or ``None`` if not loaded."""
        return self.schema

    def close(self) -> None:
        """Close all database connections."""
        logger.info("Closing QueryEngine")
        if self.duckdb_executor:
            self.duckdb_executor.close()
        if self.datasource_manager:
            self.datasource_manager.close()

    def __enter__(self) -> "QueryEngine":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def __del__(self) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_llm_client(self) -> LLMClient:
        """Instantiate the correct ``LLMClient`` from config."""
        # Load few-shot examples if configured
        few_shot: list[dict[str, str]] = []
        if self.config.few_shot_examples_path:
            try:
                few_shot = load_few_shot_examples(self.config.few_shot_examples_path)
                logger.info(f"Loaded {len(few_shot)} few-shot examples")
            except Exception as e:
                logger.warning(f"Could not load few-shot examples: {e}")

        provider = self.config.llm_provider.lower()

        if provider == "openai":
            if not self.config.openai_api_key:
                raise ConfigurationError(
                    "openai_api_key is required when llm_provider='openai'. "
                    "Set QUERY_ENGINE_OPENAI_API_KEY in your environment or .env file."
                )
            return openai_client(
                api_key=self.config.openai_api_key,
                model=self.config.llm_model,
                temperature=self.config.llm_temperature,
                max_tokens=self.config.llm_max_tokens,
                few_shot_examples=few_shot or None,
            )

        if provider == "anthropic":
            if not self.config.anthropic_api_key:
                raise ConfigurationError(
                    "anthropic_api_key is required when llm_provider='anthropic'. "
                    "Set QUERY_ENGINE_ANTHROPIC_API_KEY in your environment or .env file."
                )
            return anthropic_client(
                api_key=self.config.anthropic_api_key,
                model=self.config.llm_model,
                temperature=self.config.llm_temperature,
                max_tokens=self.config.llm_max_tokens,
                few_shot_examples=few_shot or None,
            )

        raise ConfigurationError(
            f"Unknown llm_provider: {self.config.llm_provider!r}. "
            "Supported values: 'openai', 'anthropic'."
        )

    def _build_context(self) -> str:
        """Serialise the datasource schema to a markdown context string."""
        if not self.schema:
            return ""

        parts: list[str] = [f"# {self.schema.name}"]
        if self.schema.description:
            parts.append(self.schema.description)
        parts.append("\n## Available Tables:\n")
        for table in self.schema.tables:
            parts.append(f"### {table.name}")
            if table.description:
                parts.append(table.description)
            if table.row_count:
                parts.append(f"Rows: {table.row_count}")
            parts.append("\nColumns:")
            for col in table.columns:
                nullable = " (nullable)" if col.nullable else " (required)"
                parts.append(f"- {col.name}: {col.type}{nullable}")
        return "\n".join(parts)
