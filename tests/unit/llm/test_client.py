"""Unit tests for LLMClient and factory helpers."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from langchain_core.messages import AIMessage

from query_engine.llm.client import LLMClient, load_few_shot_examples
from query_engine.utils import APIParsingError

# ---------------------------------------------------------------------------
# _extract_sql (static helper)
# ---------------------------------------------------------------------------

_extract_sql = LLMClient._extract_sql  # convenience alias


class TestExtractSql:
    def test_extracts_from_sql_fence(self) -> None:
        assert _extract_sql("```sql\nSELECT 1\n```") == "SELECT 1"

    def test_extracts_from_plain_fence(self) -> None:
        assert _extract_sql("```\nSELECT 2\n```") == "SELECT 2"

    def test_returns_bare_string_when_no_fence(self) -> None:
        assert _extract_sql("SELECT 3") == "SELECT 3"

    def test_strips_whitespace(self) -> None:
        assert _extract_sql("```sql\n  SELECT 4  \n```") == "SELECT 4"

    def test_raises_on_empty_string(self) -> None:
        with pytest.raises(APIParsingError):
            _extract_sql("")

    def test_raises_on_whitespace_only(self) -> None:
        with pytest.raises(APIParsingError):
            _extract_sql("   ")

    def test_multiline_sql(self) -> None:
        raw = "```sql\nSELECT a, b\nFROM t\nWHERE x = 1\n```"
        result = _extract_sql(raw)
        assert "SELECT a, b" in result
        assert "FROM t" in result


# ---------------------------------------------------------------------------
# LLMClient — generate_sql (chains mocked via llm_client fixture)
# ---------------------------------------------------------------------------


class TestGenerateSql:
    def test_returns_extracted_sql(self, llm_client: LLMClient) -> None:
        llm_client._sql_chain.invoke.return_value = AIMessage(  # type: ignore[union-attr]
            content="```sql\nSELECT COUNT(*) FROM t\n```"
        )
        result = llm_client.generate_sql("schema ctx", "how many rows?")
        assert result == "SELECT COUNT(*) FROM t"

    def test_calls_chain_once(self, llm_client: LLMClient) -> None:
        llm_client._sql_chain.invoke.return_value = AIMessage(content="```sql\nSELECT 1\n```")  # type: ignore[union-attr]
        llm_client.generate_sql("ctx", "q")
        assert llm_client._sql_chain.invoke.call_count == 1  # type: ignore[union-attr]

    def test_raises_when_chain_returns_empty(self, llm_client: LLMClient) -> None:
        llm_client._sql_chain.invoke.return_value = AIMessage(content="   ")  # type: ignore[union-attr]
        with pytest.raises(APIParsingError):
            llm_client.generate_sql("ctx", "q")

    def test_propagates_chain_exception(self, llm_client: LLMClient) -> None:
        llm_client._sql_chain.invoke.side_effect = RuntimeError("network error")  # type: ignore[union-attr]
        with pytest.raises(RuntimeError, match="network error"):
            llm_client.generate_sql("ctx", "q")


# ---------------------------------------------------------------------------
# LLMClient — debug_sql
# ---------------------------------------------------------------------------


class TestDebugSql:
    def test_returns_fixed_sql(self, llm_client: LLMClient) -> None:
        llm_client._debug_chain.invoke.return_value = AIMessage(  # type: ignore[union-attr]
            content="```sql\nSELECT * FROM transactions\n```"
        )
        result = llm_client.debug_sql("ctx", "SELECT * FORM t", "syntax error", attempt=1)
        assert result == "SELECT * FROM transactions"

    def test_attempt_number_in_invoke_input(self, llm_client: LLMClient) -> None:
        llm_client._debug_chain.invoke.return_value = AIMessage(content="```sql\nSELECT 1\n```")  # type: ignore[union-attr]
        llm_client.debug_sql("ctx", "bad sql", "err", attempt=3)
        call_kwargs = llm_client._debug_chain.invoke.call_args[0][0]  # type: ignore[union-attr]
        assert call_kwargs["attempt"] == 3


# ---------------------------------------------------------------------------
# LLMClient — synthesize_answer
# ---------------------------------------------------------------------------


class TestSynthesizeAnswer:
    def test_returns_answer_string(self, llm_client: LLMClient) -> None:
        llm_client._synthesis_chain.invoke.return_value = AIMessage(content="There are 42 rows.")  # type: ignore[union-attr]
        result = llm_client.synthesize_answer([{"n": 42}], "how many?", 100.0)
        assert result == "There are 42 rows."

    def test_chain_invoked_once(self, llm_client: LLMClient) -> None:
        llm_client._synthesis_chain.invoke.return_value = AIMessage(content="ok")  # type: ignore[union-attr]
        llm_client.synthesize_answer([{"i": i} for i in range(20)], "q", 0.0)
        assert llm_client._synthesis_chain.invoke.call_count == 1  # type: ignore[union-attr]

    def test_fallback_on_empty_content(self, llm_client: LLMClient) -> None:
        llm_client._synthesis_chain.invoke.return_value = AIMessage(content="")  # type: ignore[union-attr]
        result = llm_client.synthesize_answer([], "q", 0.0)
        assert "0 results" in result


# ---------------------------------------------------------------------------
# Token tracking
# ---------------------------------------------------------------------------


class TestTokenTracking:
    def test_initial_count_is_zero(self, llm_client: LLMClient) -> None:
        assert llm_client.get_token_count() == 0

    def test_count_increments_with_usage_metadata(self, llm_client: LLMClient) -> None:
        msg = AIMessage(content="```sql\nSELECT 1\n```")
        msg.usage_metadata = {"total_tokens": 50}  # type: ignore[attr-defined]
        llm_client._sql_chain.invoke.return_value = msg  # type: ignore[union-attr]
        llm_client.generate_sql("ctx", "q")
        assert llm_client.get_token_count() == 50

    def test_count_accumulates_across_calls(self, llm_client: LLMClient) -> None:
        def make_msg(tokens: int) -> AIMessage:
            msg = AIMessage(content="```sql\nSELECT 1\n```")
            msg.usage_metadata = {"total_tokens": tokens}  # type: ignore[attr-defined]
            return msg

        llm_client._sql_chain.invoke.side_effect = [make_msg(30), make_msg(20)]  # type: ignore[union-attr]
        llm_client.generate_sql("ctx", "q1")
        llm_client.generate_sql("ctx", "q2")
        assert llm_client.get_token_count() == 50


# ---------------------------------------------------------------------------
# Few-shot examples
# ---------------------------------------------------------------------------


class TestFewShotIntegration:
    def test_few_shot_examples_builds_client(self, mock_llm: MagicMock) -> None:
        examples = [{"question": "How many rows?", "sql": "SELECT COUNT(*) FROM t"}]
        # Should not raise
        client = LLMClient(mock_llm, few_shot_examples=examples)
        assert client is not None

    def test_no_few_shot_examples_also_works(self, mock_llm: MagicMock) -> None:
        client = LLMClient(mock_llm, few_shot_examples=[])
        assert client is not None


# ---------------------------------------------------------------------------
# load_few_shot_examples
# ---------------------------------------------------------------------------


class TestLoadFewShotExamples:
    def test_loads_from_fixture(self) -> None:
        examples = load_few_shot_examples("fixtures/example_queries.yaml")
        assert len(examples) > 0
        assert "question" in examples[0]
        assert "sql" in examples[0]

    def test_returns_list_of_dicts(self) -> None:
        examples = load_few_shot_examples("fixtures/example_queries.yaml")
        for ex in examples:
            assert isinstance(ex["question"], str)
            assert isinstance(ex["sql"], str)

    def test_missing_file_raises(self) -> None:
        with pytest.raises(FileNotFoundError):
            load_few_shot_examples("nonexistent.yaml")
