from unittest.mock import MagicMock

import pytest

from nlqe.testing.datasets import GoldenDataset, GoldenTestCase
from nlqe.testing.evaluator import Evaluator
from nlqe.testing.metrics import (
    AnswerQualityMetric,
    ConfidenceCalibration,
    ResultCorrectnessMetric,
)


@pytest.fixture
def mock_query_engine():
    engine = MagicMock()
    # Setup mock query response
    response = MagicMock()
    response.generated_sql = "SELECT * FROM test"
    response.data = [{"val": 1}]
    response.answer = "The answer is 1."
    response.confidence_score = 0.9
    engine.query.return_value = response
    return engine


@pytest.fixture
def mock_dataset():
    tc1 = GoldenTestCase(
        id="tc1",
        category="cat1",
        difficulty="easy",
        description="desc1",
        datasource={"type": "parquet", "path": "test"},
        user_query="Query 1",
        expected_sql="SELECT * FROM test",
        expected_results=[{"val": 1}],
        expected_answer_summary="Answer is 1",
    )
    tc2 = GoldenTestCase(
        id="tc2",
        category="cat2",
        difficulty="hard",
        description="desc2",
        datasource={"type": "parquet", "path": "test"},
        user_query="Query 2",
        expected_sql="SELECT * FROM test2",
        expected_results=[{"val": 2}],
        expected_answer_summary="Answer is 2",
    )

    dataset = MagicMock(spec=GoldenDataset)
    dataset.count = 2
    dataset.datasets = [tc1, tc2]
    dataset.categories = ["cat1", "cat2"]
    dataset.difficulties = ["easy", "hard"]

    def get_by_category(cat):
        return [tc for tc in [tc1, tc2] if tc.category == cat]

    dataset.get_by_category.side_effect = get_by_category

    def get_by_difficulty(diff):
        return [tc for tc in [tc1, tc2] if tc.difficulty == diff]

    dataset.get_by_difficulty.side_effect = get_by_difficulty

    return dataset


@pytest.fixture
def mock_quality_evaluator():
    evaluator = MagicMock()
    metric = AnswerQualityMetric(
        score=0.8,
        factual_accuracy=True,
        completeness=True,
        relevance=True,
        clarity=True,
        reasoning="Good enough",
    )
    evaluator.evaluate.return_value = metric
    return evaluator


def test_evaluator_evaluate_all(mock_query_engine, mock_dataset, mock_quality_evaluator):
    evaluator = Evaluator(
        query_engine=mock_query_engine,
        golden_dataset=mock_dataset,
        answer_quality_evaluator=mock_quality_evaluator,
    )

    # We also need to mock MetricsCalculator.calculate_result_correctness and calculate_confidence_calibration
    # since they are static methods
    with pytest.MonkeyPatch.context() as m:
        m.setattr(
            "nlqe.testing.evaluator.MetricsCalculator.calculate_result_correctness",
            lambda **kwargs: ResultCorrectnessMetric(
                score=1.0,
                is_correct=True,
                missing_rows=0,
                extra_rows=0,
                mismatched_values=0,
                row_count_match=True,
                columns_match=True,
                values_match=True,
            ),
        )
        m.setattr(
            "nlqe.testing.evaluator.MetricsCalculator.calculate_confidence_calibration",
            lambda **kwargs: ConfidenceCalibration(
                predicted_confidence=0.9,
                actual_accuracy=0.9,
                calibration_error=0.0,
                is_calibrated=True,
            ),
        )

        metrics = evaluator.evaluate_all()

        assert metrics.total_tests == 2
        assert metrics.passed_tests == 2
        assert metrics.failed_tests == 0
        assert metrics.accuracy == 1.0
        assert metrics.avg_result_correctness == 1.0
        assert metrics.avg_answer_quality == 0.8

        assert len(evaluator.results) == 2
        assert len(evaluator.get_failed_tests()) == 0
        assert len(evaluator.get_results_by_category("cat1")) == 1
        assert len(evaluator.get_results_by_difficulty("easy")) == 1


def test_evaluate_by_category(mock_query_engine, mock_dataset, mock_quality_evaluator):
    evaluator = Evaluator(
        query_engine=mock_query_engine,
        golden_dataset=mock_dataset,
        answer_quality_evaluator=mock_quality_evaluator,
    )

    with pytest.MonkeyPatch.context() as m:
        m.setattr(
            "nlqe.testing.evaluator.MetricsCalculator.calculate_result_correctness",
            lambda **kwargs: ResultCorrectnessMetric(
                score=1.0,
                is_correct=True,
                missing_rows=0,
                extra_rows=0,
                mismatched_values=0,
                row_count_match=True,
                columns_match=True,
                values_match=True,
            ),
        )
        m.setattr(
            "nlqe.testing.evaluator.MetricsCalculator.calculate_confidence_calibration",
            lambda **kwargs: ConfidenceCalibration(
                predicted_confidence=0.9,
                actual_accuracy=0.9,
                calibration_error=0.0,
                is_calibrated=True,
            ),
        )

        metrics = evaluator.evaluate_by_category("cat1")
        assert metrics.total_tests == 1
        assert metrics.passed_tests == 1

        # Original results shouldn't be overridden permanently
        assert len(evaluator.results) == 0


def test_evaluate_by_difficulty(mock_query_engine, mock_dataset, mock_quality_evaluator):
    evaluator = Evaluator(
        query_engine=mock_query_engine,
        golden_dataset=mock_dataset,
        answer_quality_evaluator=mock_quality_evaluator,
    )

    with pytest.MonkeyPatch.context() as m:
        m.setattr(
            "nlqe.testing.evaluator.MetricsCalculator.calculate_result_correctness",
            lambda **kwargs: ResultCorrectnessMetric(
                score=1.0,
                is_correct=True,
                missing_rows=0,
                extra_rows=0,
                mismatched_values=0,
                row_count_match=True,
                columns_match=True,
                values_match=True,
            ),
        )
        m.setattr(
            "nlqe.testing.evaluator.MetricsCalculator.calculate_confidence_calibration",
            lambda **kwargs: ConfidenceCalibration(
                predicted_confidence=0.9,
                actual_accuracy=0.9,
                calibration_error=0.0,
                is_calibrated=True,
            ),
        )

        metrics = evaluator.evaluate_by_difficulty("hard")
        assert metrics.total_tests == 1
        assert metrics.passed_tests == 1


def test_evaluate_single_error(mock_query_engine, mock_dataset, mock_quality_evaluator):
    mock_query_engine.query.side_effect = Exception("Query Failed")

    evaluator = Evaluator(
        query_engine=mock_query_engine,
        golden_dataset=mock_dataset,
        answer_quality_evaluator=mock_quality_evaluator,
    )

    tc = mock_dataset.datasets[0]
    result = evaluator._evaluate_single(tc)

    assert result.success is False
    assert result.error == "Query Failed"
