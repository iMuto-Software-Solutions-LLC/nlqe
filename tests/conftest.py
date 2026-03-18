"""Shared pytest fixtures for the query-engine test suite.

All tests run without a real LLM or DuckDB connection by default.
Fixtures that require external services are marked ``live`` and skipped
unless ``--live`` is passed on the command line.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from langchain_core.messages import AIMessage

from query_engine.config import QueryEngineConfig
from query_engine.llm.client import LLMClient
from query_engine.testing.datasets import GoldenDataset, GoldenTestCase
from query_engine.testing.metrics import (
    AnswerQualityMetric,
    EvaluationMetrics,
    ResultCorrectnessMetric,
)
from query_engine.types import (
    ColumnInfo,
    DataSourceSchema,
    DataSourceType,
    DebugInfo,
    QueryResponse,
    TableInfo,
)

# ---------------------------------------------------------------------------
# Custom markers
# ---------------------------------------------------------------------------


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--live",
        action="store_true",
        default=False,
        help="Run tests that call real LLM/DuckDB services",
    )


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "live: mark test as requiring live external services")


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if not config.getoption("--live"):
        skip_live = pytest.mark.skip(reason="Pass --live to run live service tests")
        for item in items:
            if "live" in item.keywords:
                item.add_marker(skip_live)


# ---------------------------------------------------------------------------
# Config fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def minimal_config() -> QueryEngineConfig:
    """A QueryEngineConfig with minimal settings — no real API key needed."""
    return QueryEngineConfig(
        llm_provider="openai",
        openai_api_key="test-key",
        llm_model="gpt-4o",
        llm_temperature=0.0,
        llm_max_tokens=100,
        query_timeout_seconds=5,
        max_debug_attempts=2,
        log_queries=False,
    )


# ---------------------------------------------------------------------------
# LLM mock fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_llm() -> MagicMock:
    """A mock BaseChatModel.

    NOTE: This mock is used to construct an LLMClient and verify the chain is
    wired correctly.  To control what generate_sql / debug_sql / synthesize_answer
    return, mock the LLMClient methods directly instead (see ``mock_llm_client``).
    """
    llm = MagicMock()
    return llm


@pytest.fixture
def mock_llm_client() -> MagicMock:
    """A fully-mocked LLMClient — use this in QueryLoop / QueryEngine tests."""
    client = MagicMock(spec=LLMClient)
    client.generate_sql.return_value = "SELECT COUNT(*) AS total FROM transactions"
    client.synthesize_answer.return_value = "There are 42 rows."
    client.debug_sql.return_value = "SELECT COUNT(*) AS total FROM transactions"
    return client


@pytest.fixture
def llm_client(mock_llm: MagicMock) -> LLMClient:
    """LLMClient backed by a mock LLM, with chains mocked to return valid AIMessages.

    The chains (_sql_chain, _debug_chain, _synthesis_chain) are replaced so
    that llm.invoke() on the underlying model is bypassed entirely.
    """
    client = LLMClient(mock_llm)
    # Replace the LCEL chains with simple mocks
    client._sql_chain = MagicMock()  # type: ignore[method-assign]
    client._debug_chain = MagicMock()  # type: ignore[method-assign]
    client._synthesis_chain = MagicMock()  # type: ignore[method-assign]
    client._sql_chain.invoke.return_value = AIMessage(content="```sql\nSELECT 1\n```")
    client._debug_chain.invoke.return_value = AIMessage(content="```sql\nSELECT 1\n```")
    client._synthesis_chain.invoke.return_value = AIMessage(content="Answer.")
    return client


# ---------------------------------------------------------------------------
# DuckDB mock fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_executor() -> MagicMock:
    """A mock DuckDBExecutor that returns one row successfully."""
    executor = MagicMock()
    executor.execute.return_value = (True, [{"total": 42}])
    return executor


# ---------------------------------------------------------------------------
# Schema / datasource fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def simple_schema() -> DataSourceSchema:
    """A minimal single-table schema for testing."""
    return DataSourceSchema(
        name="test_db",
        description="Test database",
        datasource_type=DataSourceType.PARQUET,
        table_count=1,
        tables=[
            TableInfo(
                name="transactions",
                description="Sample transactions",
                row_count=100,
                columns=[
                    ColumnInfo(name="id", type="INTEGER", nullable=False),
                    ColumnInfo(name="amount", type="FLOAT", nullable=True),
                    ColumnInfo(name="category", type="VARCHAR", nullable=True),
                ],
            )
        ],
    )


# ---------------------------------------------------------------------------
# QueryResponse fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def successful_response() -> QueryResponse:
    """A typical successful QueryResponse."""
    return QueryResponse(
        user_query="How many transactions?",
        generated_sql="SELECT COUNT(*) AS total FROM transactions",
        data=[{"total": 42}],
        answer="There are 42 transactions.",
        confidence_score=1.0,
        execution_time_ms=150.0,
        result_rows=1,
        debug_info=None,
        error=None,
    )


@pytest.fixture
def failed_response() -> QueryResponse:
    """A QueryResponse from a query that needed debugging."""
    return QueryResponse(
        user_query="Bad query",
        generated_sql="SELECT * FORM transactions",
        data=[],
        answer="",
        confidence_score=0.7,
        execution_time_ms=500.0,
        result_rows=0,
        debug_info=DebugInfo(
            attempts=2,
            errors=["syntax error at FORM"],
            modified_sqls=["SELECT * FROM transactions"],
            first_error="syntax error at FORM",
            final_error=None,
        ),
        error=None,
    )


# ---------------------------------------------------------------------------
# Golden dataset fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_test_case() -> GoldenTestCase:
    return GoldenTestCase(
        id="tc_001",
        category="aggregation",
        difficulty="easy",
        description="Count all rows",
        datasource={"path": "fixtures/transactions.parquet", "type": "parquet"},
        user_query="How many transactions?",
        expected_sql="SELECT COUNT(*) AS total FROM transactions",
        expected_results=[{"total": 2500}],
        expected_answer_summary="There are 2500 transactions.",
        acceptable_variance=0.0,
        priority="high",
        tags=["count", "easy"],
    )


@pytest.fixture
def sample_dataset(sample_test_case: GoldenTestCase) -> GoldenDataset:
    return GoldenDataset(
        version="1.0",
        created_date="2026-03-17",
        datasets=[sample_test_case],
    )


# ---------------------------------------------------------------------------
# Evaluation metric fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def perfect_correctness() -> ResultCorrectnessMetric:
    return ResultCorrectnessMetric(
        score=1.0,
        row_count_match=True,
        columns_match=True,
        values_match=True,
        issues=[],
    )


@pytest.fixture
def good_quality() -> AnswerQualityMetric:
    return AnswerQualityMetric(
        score=0.9,
        factual_accuracy=True,
        completeness=True,
        relevance=True,
        clarity=True,
        evaluator_notes="Excellent answer.",
    )


@pytest.fixture
def sample_metrics() -> EvaluationMetrics:
    return EvaluationMetrics(
        total_tests=10,
        passed_tests=8,
        failed_tests=2,
        accuracy=0.8,
        avg_result_correctness=0.85,
        avg_answer_quality=0.80,
        avg_confidence_score=0.90,
        confidence_calibration_error=0.05,
        execution_time_ms=1200.0,
        by_category={"aggregation": {"total": 5, "passed": 4, "avg_correctness": 0.9}},
        by_difficulty={"easy": {"total": 5, "passed": 5, "avg_correctness": 1.0}},
    )
