"""Unit tests for QueryLoop."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from nlqe.query.loop import QueryLoop
from nlqe.types import QueryResponse
from nlqe.utils import DebugFailedError, SQLSchemaError, SQLSyntaxError


def _make_loop(
    mock_llm_client: MagicMock,
    executor: MagicMock,
    max_debug_attempts: int = 3,
) -> QueryLoop:
    return QueryLoop(
        llm_client=mock_llm_client,
        duckdb_executor=executor,
        max_debug_attempts=max_debug_attempts,
    )


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


class TestQueryLoopHappyPath:
    def test_returns_query_response(
        self, mock_llm_client: MagicMock, mock_executor: MagicMock
    ) -> None:
        mock_llm_client.generate_sql.return_value = "SELECT COUNT(*) AS n FROM t"
        mock_executor.execute.return_value = (True, [{"n": 42}])
        mock_llm_client.synthesize_answer.return_value = "There are 42 rows."

        loop = _make_loop(mock_llm_client, mock_executor)
        resp = loop.execute("how many rows?", "schema ctx")

        assert isinstance(resp, QueryResponse)
        assert resp.result_rows == 1
        assert resp.data == [{"n": 42}]
        assert resp.error is None

    def test_confidence_is_1_on_clean_run(
        self, mock_llm_client: MagicMock, mock_executor: MagicMock
    ) -> None:
        mock_executor.execute.return_value = (True, [{"x": 1}])
        loop = _make_loop(mock_llm_client, mock_executor)
        resp = loop.execute("q", "ctx")
        assert resp.confidence_score == pytest.approx(1.0)

    def test_generated_sql_in_response(
        self, mock_llm_client: MagicMock, mock_executor: MagicMock
    ) -> None:
        mock_llm_client.generate_sql.return_value = "SELECT 1"
        mock_executor.execute.return_value = (True, [])
        loop = _make_loop(mock_llm_client, mock_executor)
        resp = loop.execute("q", "ctx")
        assert resp.generated_sql == "SELECT 1"

    def test_generate_sql_called_with_context_and_query(
        self, mock_llm_client: MagicMock, mock_executor: MagicMock
    ) -> None:
        mock_executor.execute.return_value = (True, [{"x": 1}])
        loop = _make_loop(mock_llm_client, mock_executor)
        loop.execute("test question", "test context")
        mock_llm_client.generate_sql.assert_called_once_with("test context", "test question")


# ---------------------------------------------------------------------------
# Debug loop
# ---------------------------------------------------------------------------


class TestQueryLoopDebug:
    def test_retries_on_syntax_error(
        self, mock_llm_client: MagicMock, mock_executor: MagicMock
    ) -> None:
        mock_executor.execute.side_effect = [
            SQLSyntaxError("syntax error"),
            (True, [{"ok": 1}]),
        ]
        mock_llm_client.debug_sql.return_value = "SELECT 1"
        loop = _make_loop(mock_llm_client, mock_executor)
        resp = loop.execute("q", "ctx")
        assert resp.result_rows == 1
        assert resp.confidence_score < 1.0

    def test_retries_on_schema_error(
        self, mock_llm_client: MagicMock, mock_executor: MagicMock
    ) -> None:
        mock_executor.execute.side_effect = [
            SQLSchemaError("unknown table"),
            (True, [{"ok": 1}]),
        ]
        mock_llm_client.debug_sql.return_value = "SELECT 1"
        loop = _make_loop(mock_llm_client, mock_executor)
        resp = loop.execute("q", "ctx")
        assert resp.result_rows == 1

    def test_raises_debug_failed_after_all_attempts(
        self, mock_llm_client: MagicMock, mock_executor: MagicMock
    ) -> None:
        mock_executor.execute.side_effect = SQLSyntaxError("bad sql")
        loop = _make_loop(mock_llm_client, mock_executor, max_debug_attempts=2)
        with pytest.raises(DebugFailedError):
            loop.execute("q", "ctx")

    def test_debug_sql_called_with_correct_args(
        self, mock_llm_client: MagicMock, mock_executor: MagicMock
    ) -> None:
        mock_executor.execute.side_effect = [
            SQLSyntaxError("syntax error here"),
            (True, [{"ok": 1}]),
        ]
        loop = _make_loop(mock_llm_client, mock_executor)
        loop.execute("q", "my context")
        mock_llm_client.debug_sql.assert_called_once()
        call_args = mock_llm_client.debug_sql.call_args
        assert call_args[0][0] == "my context"  # context
        assert "syntax error here" in call_args[0][2]  # error message

    def test_synthesize_called_on_success(
        self, mock_llm_client: MagicMock, mock_executor: MagicMock
    ) -> None:
        mock_executor.execute.return_value = (True, [{"x": 1}])
        loop = _make_loop(mock_llm_client, mock_executor)
        loop.execute("my question", "ctx")
        mock_llm_client.synthesize_answer.assert_called_once()
        call_args = mock_llm_client.synthesize_answer.call_args
        assert call_args[0][1] == "my question"  # user_query positional arg


# ---------------------------------------------------------------------------
# Confidence scoring
# ---------------------------------------------------------------------------


class TestCalculateConfidence:
    def test_no_penalties(self) -> None:
        score = QueryLoop._calculate_confidence([{"x": 1}], None, 100.0)
        assert score == pytest.approx(1.0)

    def test_penalty_for_empty_results(self) -> None:
        score = QueryLoop._calculate_confidence([], None, 100.0)
        assert score == pytest.approx(0.9)

    def test_penalty_for_slow_query(self) -> None:
        score = QueryLoop._calculate_confidence([{"x": 1}], None, 6000.0)
        assert score == pytest.approx(0.95)

    def test_penalty_for_debug_attempts(self) -> None:
        from nlqe.types import DebugInfo

        di = DebugInfo(attempts=2, errors=["e"], modified_sqls=[], first_error="e")
        score = QueryLoop._calculate_confidence([{"x": 1}], di, 100.0)
        assert score == pytest.approx(0.8)

    def test_clamped_to_zero(self) -> None:
        from nlqe.types import DebugInfo

        di = DebugInfo(attempts=10, errors=["e"], modified_sqls=[], first_error="e")
        score = QueryLoop._calculate_confidence([], di, 9999.0)
        assert score >= 0.0
