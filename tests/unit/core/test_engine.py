"""Unit tests for QueryEngine (top-level orchestrator)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from nlqe.config import QueryEngineConfig
from nlqe.engine import QueryEngine
from nlqe.types import ColumnInfo, DataSourceSchema, DataSourceType, TableInfo
from nlqe.utils import ConfigurationError


def _make_schema(name: str = "test_db") -> DataSourceSchema:
    return DataSourceSchema(
        name=name,
        datasource_type=DataSourceType.PARQUET,
        table_count=1,
        tables=[
            TableInfo(
                name="t",
                row_count=10,
                columns=[ColumnInfo(name="id", type="INTEGER")],
            )
        ],
    )


# ---------------------------------------------------------------------------
# _build_llm_client — config validation
# ---------------------------------------------------------------------------


class TestBuildLLMClient:
    def test_raises_on_unknown_provider(self) -> None:
        cfg = QueryEngineConfig(llm_provider="ollama")
        engine = QueryEngine(cfg)
        with pytest.raises(ConfigurationError, match="Unknown llm_provider"):
            engine._build_llm_client()

    def test_raises_on_openai_without_key(self) -> None:
        cfg = QueryEngineConfig(llm_provider="openai", openai_api_key="")
        engine = QueryEngine(cfg)
        with pytest.raises(ConfigurationError, match="openai_api_key is required"):
            engine._build_llm_client()

    def test_raises_on_anthropic_without_key(self) -> None:
        cfg = QueryEngineConfig(llm_provider="anthropic", anthropic_api_key="")
        engine = QueryEngine(cfg)
        with pytest.raises(ConfigurationError, match="anthropic_api_key is required"):
            engine._build_llm_client()


# ---------------------------------------------------------------------------
# query() pre-condition check
# ---------------------------------------------------------------------------


class TestEngineQueryGuard:
    def test_raises_if_no_datasource_loaded(self) -> None:
        cfg = QueryEngineConfig(openai_api_key="k")
        engine = QueryEngine(cfg)
        with pytest.raises(ValueError, match="No datasource loaded"):
            engine.query("how many rows?")

    def test_raises_if_no_datasource_for_conversation(self) -> None:
        cfg = QueryEngineConfig(openai_api_key="k")
        engine = QueryEngine(cfg)
        with pytest.raises(ValueError, match="No datasource loaded"):
            engine.start_conversation()


# ---------------------------------------------------------------------------
# _build_context
# ---------------------------------------------------------------------------


class TestBuildContext:
    def test_empty_when_no_schema(self) -> None:
        cfg = QueryEngineConfig(openai_api_key="k")
        engine = QueryEngine(cfg)
        assert engine._build_context() == ""

    def test_includes_table_name(self) -> None:
        cfg = QueryEngineConfig(openai_api_key="k")
        engine = QueryEngine(cfg)
        engine.schema = _make_schema("my_db")
        ctx = engine._build_context()
        assert "my_db" in ctx
        assert "t" in ctx
        assert "id" in ctx
        assert "INTEGER" in ctx

    def test_includes_description_when_set(self) -> None:
        cfg = QueryEngineConfig(openai_api_key="k")
        engine = QueryEngine(cfg)
        schema = _make_schema()
        schema.description = "Important dataset"
        engine.schema = schema
        ctx = engine._build_context()
        assert "Important dataset" in ctx

    def test_nullable_column_marker(self) -> None:
        cfg = QueryEngineConfig(openai_api_key="k")
        engine = QueryEngine(cfg)
        schema = _make_schema()
        schema.tables[0].columns[0].nullable = False
        engine.schema = schema
        ctx = engine._build_context()
        assert "(required)" in ctx

    def test_includes_row_count(self) -> None:
        cfg = QueryEngineConfig(openai_api_key="k")
        engine = QueryEngine(cfg)
        engine.schema = _make_schema()
        ctx = engine._build_context()
        assert "10" in ctx  # row_count from fixture


# ---------------------------------------------------------------------------
# custom_llm_client bypasses provider check
# ---------------------------------------------------------------------------


class TestCustomLLMClient:
    def test_custom_client_used_directly(self, mock_llm_client: MagicMock) -> None:
        cfg = QueryEngineConfig()  # no keys set
        engine = QueryEngine(cfg, custom_llm_client=mock_llm_client)
        assert engine.llm_client is mock_llm_client

    def test_query_uses_custom_client(
        self, mock_llm_client: MagicMock, mock_executor: MagicMock
    ) -> None:
        mock_llm_client.generate_sql.return_value = "SELECT 1"
        mock_llm_client.synthesize_answer.return_value = "One result."
        mock_executor.execute.return_value = (True, [{"x": 1}])

        cfg = QueryEngineConfig()
        engine = QueryEngine(cfg, custom_llm_client=mock_llm_client)
        engine.schema = _make_schema()
        engine.duckdb_executor = mock_executor
        from nlqe.query.loop import QueryLoop

        engine.query_loop = QueryLoop(mock_llm_client, mock_executor)

        resp = engine.query("test")
        assert resp.result_rows == 1


# ---------------------------------------------------------------------------
# context manager
# ---------------------------------------------------------------------------


class TestContextManager:
    def test_close_called_on_exit(self, mock_executor: MagicMock) -> None:
        cfg = QueryEngineConfig(openai_api_key="k")
        engine = QueryEngine(cfg)
        engine.duckdb_executor = mock_executor
        with engine:
            pass
        mock_executor.close.assert_called_once()
