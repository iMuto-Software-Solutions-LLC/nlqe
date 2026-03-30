"""LangChain-based LLM client — provider-agnostic SQL generation and answer synthesis."""

from __future__ import annotations

import re
from typing import Any

import yaml  # type: ignore[import-untyped]
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.prompts import (
    ChatPromptTemplate,
    FewShotChatMessagePromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
)

from nlqe.utils import APIParsingError, get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

_SQL_SYSTEM = SystemMessagePromptTemplate.from_template(
    """You are an expert SQL generator. Convert natural language questions into DuckDB SQL.

RULES:
1. Return ONLY valid SQL wrapped in ```sql ... ``` markers — no explanations.
2. Use DuckDB syntax (e.g. EPOCH, EXTRACT, strftime).
3. Never include multiple statements.
4. Use JOINs, aggregations, and WHERE clauses as appropriate.

Available data:
{context}"""
)

_SQL_HUMAN = HumanMessagePromptTemplate.from_template("{question}")

# Few-shot example pair template
_FEW_SHOT_EXAMPLE_PROMPT = ChatPromptTemplate.from_messages(
    [
        HumanMessagePromptTemplate.from_template("{question}"),
        AIMessage(content="```sql\n{sql}\n```"),  # type: ignore[call-arg]
    ]
)

_DEBUG_SYSTEM = SystemMessagePromptTemplate.from_template(
    """You are an expert SQL debugger. Fix the SQL query below so it runs correctly on DuckDB.

Available data:
{context}

Failed SQL (attempt {attempt}):
{failed_sql}

DuckDB error:
{error_message}

Return ONLY the corrected SQL wrapped in ```sql ... ``` markers."""
)

_DEBUG_HUMAN = HumanMessagePromptTemplate.from_template("Fix this SQL: {failed_sql}")

_SYNTHESIS_SYSTEM = SystemMessagePromptTemplate.from_template(
    """You are an expert data analyst. Explain query results in clear, conversational language.

Guidelines:
- Be concise and highlight key numbers.
- Round large numbers for readability.
- If results are empty, say so clearly.

User question: {question}

Results (JSON, up to 10 rows):
{results_json}"""
)

_SYNTHESIS_HUMAN = HumanMessagePromptTemplate.from_template("Explain these results: {results_json}")


# ---------------------------------------------------------------------------
# LLMClient
# ---------------------------------------------------------------------------


class LLMClient:
    """Provider-agnostic LLM client built on LangChain LCEL.

    Supports any ``BaseChatModel`` — OpenAI, Anthropic, Ollama, Azure, etc.
    Pass in a pre-configured model instance; the client builds LCEL chains
    from it.

    Example::

        from langchain_openai import ChatOpenAI
        from nlqe.llm.client import LLMClient

        client = LLMClient(ChatOpenAI(model="gpt-4o", temperature=0))
        sql = client.generate_sql(context="...", user_query="total sales?")

    Example with Anthropic::

        from langchain_anthropic import ChatAnthropic

        client = LLMClient(ChatAnthropic(model="claude-3-5-sonnet-20241022"))
    """

    def __init__(
        self,
        llm: BaseChatModel,
        few_shot_examples: list[dict[str, str]] | None = None,
    ) -> None:
        """Initialise the client.

        Args:
            llm: Any LangChain ``BaseChatModel`` instance.
            few_shot_examples: Optional list of ``{"question": ..., "sql": ...}``
                dicts.  When provided they are injected into the SQL-generation
                prompt as few-shot demonstrations.
        """
        self.llm = llm
        self.token_count = 0

        # Build chains once at init time
        self._sql_chain = self._build_sql_chain(few_shot_examples or [])
        self._debug_chain = self._build_debug_chain()
        self._synthesis_chain = self._build_synthesis_chain()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_sql(self, context: str, user_query: str) -> str:
        """Generate SQL from a natural-language question.

        Args:
            context: Markdown schema description built by ``QueryEngine``.
            user_query: Natural language question from the user.

        Returns:
            Extracted SQL string (no markdown fences).

        Raises:
            APIParsingError: If the LLM response contains no extractable SQL.
        """
        logger.info(f"Generating SQL for: {user_query!r}")
        response: AIMessage = self._sql_chain.invoke({"context": context, "question": user_query})
        self._track_tokens(response)
        return self._extract_sql(response.content)  # type: ignore[arg-type]

    def debug_sql(self, context: str, failed_sql: str, error_message: str, attempt: int = 1) -> str:
        """Ask the LLM to fix a failing SQL query.

        Args:
            context: Markdown schema description.
            failed_sql: The SQL that raised an error.
            error_message: The DuckDB error string.
            attempt: Current attempt number (injected into the prompt).

        Returns:
            Corrected SQL string.

        Raises:
            APIParsingError: If the LLM response contains no extractable SQL.
        """
        logger.info(f"Debugging SQL (attempt {attempt})")
        response: AIMessage = self._debug_chain.invoke(
            {
                "context": context,
                "failed_sql": failed_sql,
                "error_message": error_message,
                "attempt": attempt,
            }
        )
        self._track_tokens(response)
        return self._extract_sql(response.content)  # type: ignore[arg-type]

    def synthesize_answer(
        self,
        query_results: list[dict[str, Any]],
        user_query: str,
        execution_time_ms: float,
    ) -> str:
        """Synthesise a conversational answer from raw query results.

        Args:
            query_results: List of result dicts from DuckDB.
            user_query: Original user question.
            execution_time_ms: Execution time (not sent to LLM; kept for
                compatibility with ``QueryLoop``).

        Returns:
            Natural-language answer string.
        """
        import json

        results_json = json.dumps(query_results[:10], default=str, indent=2)
        logger.info("Synthesising answer")
        response: AIMessage = self._synthesis_chain.invoke(
            {"question": user_query, "results_json": results_json}
        )
        self._track_tokens(response)
        return response.content or f"Query returned {len(query_results)} results"  # type: ignore[return-value]

    def get_token_count(self) -> int:
        """Return cumulative token count (best-effort; not all providers report usage)."""
        return self.token_count

    # ------------------------------------------------------------------
    # Chain builders
    # ------------------------------------------------------------------

    def _build_sql_chain(self, few_shot_examples: list[dict[str, str]]) -> Any:
        """Build the SQL-generation LCEL chain."""
        if few_shot_examples:
            few_shot = FewShotChatMessagePromptTemplate(
                examples=few_shot_examples,
                example_prompt=_FEW_SHOT_EXAMPLE_PROMPT,
            )
            prompt = ChatPromptTemplate.from_messages([_SQL_SYSTEM, few_shot, _SQL_HUMAN])
        else:
            prompt = ChatPromptTemplate.from_messages([_SQL_SYSTEM, _SQL_HUMAN])

        return prompt | self.llm

    def _build_debug_chain(self) -> Any:
        """Build the SQL-debug LCEL chain."""
        prompt = ChatPromptTemplate.from_messages([_DEBUG_SYSTEM, _DEBUG_HUMAN])
        return prompt | self.llm

    def _build_synthesis_chain(self) -> Any:
        """Build the answer-synthesis LCEL chain."""
        prompt = ChatPromptTemplate.from_messages([_SYNTHESIS_SYSTEM, _SYNTHESIS_HUMAN])
        return prompt | self.llm

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_sql(response: str) -> str:
        """Extract the raw SQL from a markdown-fenced LLM response.

        Tries ``sql fences → plain fences → raw string``.

        Raises:
            APIParsingError: If no SQL can be found.
        """
        # ```sql ... ```
        m = re.findall(r"```sql\n(.*?)\n```", response, re.DOTALL)
        if m:
            return str(m[0]).strip()
        # ``` ... ```
        m = re.findall(r"```\n(.*?)\n```", response, re.DOTALL)
        if m:
            return str(m[0]).strip()
        # bare string
        sql = response.strip()
        if sql:
            return sql
        raise APIParsingError(f"Could not extract SQL from response: {response}")

    def _track_tokens(self, message: AIMessage) -> None:
        """Add token usage from a response to the running total."""
        usage = getattr(message, "usage_metadata", None)
        if usage:
            total = usage.get("total_tokens", 0)
            self.token_count += total


# ---------------------------------------------------------------------------
# Factory helpers — create a pre-configured LLMClient for common providers
# ---------------------------------------------------------------------------


def openai_client(
    api_key: str,
    model: str = "gpt-4o",
    temperature: float = 0.0,
    max_tokens: int = 2000,
    few_shot_examples: list[dict[str, str]] | None = None,
) -> LLMClient:
    """Create an ``LLMClient`` backed by OpenAI.

    Args:
        api_key: OpenAI API key.
        model: Model name (default: ``gpt-4o``).
        temperature: Generation temperature.
        max_tokens: Max completion tokens.
        few_shot_examples: Optional few-shot SQL examples.

    Returns:
        Configured ``LLMClient``.
    """
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(
        api_key=api_key,  # type: ignore[arg-type]
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,  # type: ignore[call-arg]
    )
    return LLMClient(llm, few_shot_examples=few_shot_examples)


def anthropic_client(
    api_key: str,
    model: str = "claude-3-5-sonnet-20241022",
    temperature: float = 0.0,
    max_tokens: int = 2000,
    few_shot_examples: list[dict[str, str]] | None = None,
) -> LLMClient:
    """Create an ``LLMClient`` backed by Anthropic.

    Args:
        api_key: Anthropic API key.
        model: Model name.
        temperature: Generation temperature.
        max_tokens: Max completion tokens.
        few_shot_examples: Optional few-shot SQL examples.

    Returns:
        Configured ``LLMClient``.
    """
    from langchain_anthropic import ChatAnthropic

    llm = ChatAnthropic(
        api_key=api_key,  # type: ignore[arg-type]
        model=model,  # type: ignore[call-arg]
        temperature=temperature,
        max_tokens=max_tokens,  # type: ignore[call-arg]
    )
    return LLMClient(llm, few_shot_examples=few_shot_examples)


def load_few_shot_examples(yaml_path: str) -> list[dict[str, str]]:
    """Load few-shot SQL examples from the ``example_queries.yaml`` fixture.

    Args:
        yaml_path: Path to the YAML file.

    Returns:
        List of ``{"question": ..., "sql": ...}`` dicts suitable for
        ``LLMClient``'s ``few_shot_examples`` parameter.
    """
    with open(yaml_path) as f:
        data = yaml.safe_load(f)
    examples = []
    for ex in data.get("examples", []):
        if "question" in ex and "sql" in ex:
            examples.append({"question": ex["question"], "sql": str(ex["sql"]).strip()})
    return examples
