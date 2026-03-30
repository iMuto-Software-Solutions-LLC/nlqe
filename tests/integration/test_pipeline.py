"""Integration tests for the full query pipeline (no real LLM, real DuckDB).

These tests use a real DuckDB in-memory database with the parquet fixture so
that DuckDB execution is genuine, while the LLM is mocked at the ``LLMClient``
method level (not the underlying model level, which would require navigating
the LCEL chain).

Run with:  pytest tests/integration/ -v
Live tests (requiring a real API key):  pytest tests/integration/ -v --live
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock

import pytest

from nlqe.config import QueryEngineConfig
from nlqe.engine import QueryEngine
from nlqe.llm.client import LLMClient
from nlqe.types import QueryResponse
from nlqe.utils import DebugFailedError

FIXTURE_PARQUET = "fixtures/transactions.parquet"


def _make_engine(parquet_path: str = FIXTURE_PARQUET) -> QueryEngine:
    """Build a QueryEngine with a mock LLMClient and real DuckDB."""
    cfg = QueryEngineConfig(log_queries=False)
    mock_client = MagicMock(spec=LLMClient)
    engine = QueryEngine(cfg, custom_llm_client=mock_client)
    engine.load_datasource(parquet_path)
    return engine


# ---------------------------------------------------------------------------
# Full pipeline: mock LLMClient + real DuckDB parquet
# ---------------------------------------------------------------------------


class TestFullPipelineMockedLLM:
    @pytest.fixture(autouse=True)
    def skip_if_no_fixture(self) -> None:
        if not os.path.exists(FIXTURE_PARQUET):
            pytest.skip("fixtures/transactions.parquet not found — run create_sample_data.py")

    def test_count_all_transactions(self) -> None:
        engine = _make_engine()
        engine.llm_client.generate_sql.return_value = (  # type: ignore[union-attr]
            "SELECT COUNT(*) AS total FROM transactions"
        )
        engine.llm_client.synthesize_answer.return_value = "There are 2500 transactions."  # type: ignore[union-attr]

        resp = engine.query("how many transactions?")
        assert isinstance(resp, QueryResponse)
        assert resp.result_rows == 1
        assert resp.data[0]["total"] == 2500
        assert resp.confidence_score == pytest.approx(1.0)
        engine.close()

    def test_filter_by_category(self) -> None:
        engine = _make_engine()
        engine.llm_client.generate_sql.return_value = (  # type: ignore[union-attr]
            "SELECT COUNT(*) AS n FROM transactions WHERE category = 'Electronics'"
        )
        engine.llm_client.synthesize_answer.return_value = "Found electronics."  # type: ignore[union-attr]

        resp = engine.query("how many electronics?")
        assert resp.data[0]["n"] > 0
        engine.close()

    def test_group_by_category(self) -> None:
        engine = _make_engine()
        engine.llm_client.generate_sql.return_value = (  # type: ignore[union-attr]
            "SELECT category, SUM(amount) AS total FROM transactions "
            "GROUP BY category ORDER BY total DESC"
        )
        engine.llm_client.synthesize_answer.return_value = "Revenue by category."  # type: ignore[union-attr]

        resp = engine.query("total revenue by category")
        assert resp.result_rows > 1
        categories = {r["category"] for r in resp.data}
        assert len(categories) > 1
        engine.close()

    def test_debug_loop_fixes_bad_sql(self) -> None:
        """LLM generates bad SQL first, then provides a fix."""
        engine = _make_engine()
        engine.llm_client.generate_sql.return_value = "SELECT COUNT(*) FORM transactions"  # type: ignore[union-attr]
        engine.llm_client.debug_sql.return_value = (  # type: ignore[union-attr]
            "SELECT COUNT(*) AS total FROM transactions"
        )
        engine.llm_client.synthesize_answer.return_value = "2500 transactions."  # type: ignore[union-attr]

        resp = engine.query("how many?")
        assert resp.data[0]["total"] == 2500
        assert resp.confidence_score < 1.0  # penalised for debug
        engine.close()

    def test_raises_on_persistently_bad_sql(self) -> None:
        """When LLM cannot fix SQL within max_debug_attempts, DebugFailedError is raised."""
        cfg = QueryEngineConfig(max_debug_attempts=2, log_queries=False)
        mock_client = MagicMock(spec=LLMClient)
        mock_client.generate_sql.return_value = "INVALID GARBAGE SQL"
        mock_client.debug_sql.return_value = "STILL GARBAGE"
        engine = QueryEngine(cfg, custom_llm_client=mock_client)
        engine.load_datasource(FIXTURE_PARQUET)
        with pytest.raises(DebugFailedError):
            engine.query("q")
        engine.close()

    def test_aggregation_sum(self) -> None:
        engine = _make_engine()
        engine.llm_client.generate_sql.return_value = (  # type: ignore[union-attr]
            "SELECT SUM(amount) AS total_revenue FROM transactions"
        )
        engine.llm_client.synthesize_answer.return_value = "Total revenue."  # type: ignore[union-attr]

        resp = engine.query("total revenue?")
        assert resp.result_rows == 1
        assert resp.data[0]["total_revenue"] > 0
        engine.close()

    def test_join_query(self) -> None:
        # DuckDB engine loads only transactions.parquet, so use a self-join or
        # a simple GROUP BY on an existing column instead of joining regions.
        engine = _make_engine()
        engine.llm_client.generate_sql.return_value = (  # type: ignore[union-attr]
            "SELECT region_id, COUNT(*) AS n FROM transactions GROUP BY region_id ORDER BY n DESC"
        )
        engine.llm_client.synthesize_answer.return_value = "Region breakdown."  # type: ignore[union-attr]

        resp = engine.query("transactions per region?")
        assert resp.result_rows > 1
        engine.close()


# ---------------------------------------------------------------------------
# Conversation integration: mock LLMClient + real DuckDB
# ---------------------------------------------------------------------------


class TestConversationIntegration:
    @pytest.fixture(autouse=True)
    def skip_if_no_fixture(self) -> None:
        if not os.path.exists(FIXTURE_PARQUET):
            pytest.skip("fixtures/transactions.parquet not found")

    def _make_conv_engine(self) -> QueryEngine:
        return _make_engine()

    def test_multi_turn_history_grows(self) -> None:
        engine = self._make_conv_engine()
        engine.llm_client.generate_sql.side_effect = [  # type: ignore[union-attr]
            "SELECT COUNT(*) AS n FROM transactions",
            "SELECT MAX(amount) AS mx FROM transactions",
        ]
        engine.llm_client.synthesize_answer.side_effect = [  # type: ignore[union-attr]
            "2500 transactions.",
            "Max is $2000.",
        ]
        conv = engine.start_conversation()
        r1 = conv.query("how many?")
        r2 = conv.query("max amount?")
        assert r1.turn_number == 1
        assert r2.turn_number == 2
        assert len(conv.get_history()) == 2
        engine.close()

    def test_context_includes_history_after_first_turn(self) -> None:
        engine = self._make_conv_engine()
        engine.llm_client.generate_sql.side_effect = [  # type: ignore[union-attr]
            "SELECT COUNT(*) AS n FROM transactions",
            "SELECT 1",
        ]
        engine.llm_client.synthesize_answer.side_effect = ["2500.", "ok"]  # type: ignore[union-attr]
        conv = engine.start_conversation()
        conv.query("first question")
        ctx = conv.get_context()
        assert "first question" in ctx
        engine.close()

    def test_clear_resets_history(self) -> None:
        engine = self._make_conv_engine()
        engine.llm_client.generate_sql.return_value = "SELECT 1"  # type: ignore[union-attr]
        engine.llm_client.synthesize_answer.return_value = "ok"  # type: ignore[union-attr]
        conv = engine.start_conversation()
        conv.query("test")
        assert len(conv.get_history()) == 1
        conv.clear()
        assert len(conv.get_history()) == 0
        assert conv.turn_number == 0
        engine.close()


# ---------------------------------------------------------------------------
# Live tests (require API key; skipped by default)
# ---------------------------------------------------------------------------


@pytest.mark.live
class TestLivePipeline:
    """Full end-to-end tests with a real LLM API call.

    Run with:  pytest tests/integration/ -v --live
    Requires NLQE_OPENAI_API_KEY to be set.
    """

    @pytest.fixture(autouse=True)
    def skip_if_no_fixture(self) -> None:
        if not os.path.exists(FIXTURE_PARQUET):
            pytest.skip("fixtures/transactions.parquet not found")

    def test_live_count_query(self) -> None:
        cfg = QueryEngineConfig()
        engine = QueryEngine(cfg)
        engine.load_datasource(FIXTURE_PARQUET)
        resp = engine.query("How many transactions are there in total?")
        assert resp.result_rows >= 1
        assert next(iter(resp.data[0].values())) == 2500
        engine.close()
