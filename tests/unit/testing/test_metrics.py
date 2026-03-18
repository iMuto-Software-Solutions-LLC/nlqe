"""Unit tests for MetricsCalculator and AnswerQualityEvaluator."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from query_engine.testing.metrics import (
    AnswerQualityEvaluator,
    EvaluationMetrics,
    MetricsCalculator,
)

# ---------------------------------------------------------------------------
# MetricsCalculator.calculate_result_correctness
# ---------------------------------------------------------------------------


class TestResultCorrectness:
    def test_perfect_match(self) -> None:
        actual = [{"a": 1, "b": "x"}]
        expected = [{"a": 1, "b": "x"}]
        m = MetricsCalculator.calculate_result_correctness(actual, expected)
        assert m.score == 1.0
        assert m.row_count_match is True
        assert m.columns_match is True
        assert m.values_match is True
        assert m.issues == []

    def test_row_count_mismatch_penalises_score(self) -> None:
        actual = [{"a": 1}]
        expected = [{"a": 1}, {"a": 2}]
        m = MetricsCalculator.calculate_result_correctness(actual, expected)
        assert m.row_count_match is False
        assert m.score < 1.0
        assert any("Row count" in issue for issue in m.issues)

    def test_missing_column_penalises_score(self) -> None:
        actual = [{"a": 1}]
        expected = [{"a": 1, "b": 2}]
        m = MetricsCalculator.calculate_result_correctness(actual, expected)
        assert m.columns_match is False
        assert m.score < 1.0

    def test_extra_column_penalises_score(self) -> None:
        actual = [{"a": 1, "b": 2, "c": 3}]
        expected = [{"a": 1, "b": 2}]
        m = MetricsCalculator.calculate_result_correctness(actual, expected)
        assert m.columns_match is False

    def test_value_mismatch_penalises(self) -> None:
        actual = [{"a": 99}]
        expected = [{"a": 1}]
        m = MetricsCalculator.calculate_result_correctness(actual, expected)
        assert m.values_match is False

    def test_numeric_variance_within_tolerance(self) -> None:
        actual = [{"revenue": 100.0}]
        expected = [{"revenue": 104.0}]
        m = MetricsCalculator.calculate_result_correctness(
            actual, expected, acceptable_variance=0.05
        )
        assert m.values_match is True

    def test_numeric_variance_exceeds_tolerance(self) -> None:
        actual = [{"revenue": 80.0}]
        expected = [{"revenue": 100.0}]
        m = MetricsCalculator.calculate_result_correctness(
            actual, expected, acceptable_variance=0.05
        )
        assert m.values_match is False

    def test_empty_both(self) -> None:
        m = MetricsCalculator.calculate_result_correctness([], [])
        assert m.score == 1.0
        assert m.row_count_match is True

    def test_empty_actual_nonempty_expected(self) -> None:
        m = MetricsCalculator.calculate_result_correctness([], [{"a": 1}])
        assert m.row_count_match is False
        assert m.score < 1.0

    def test_score_clamped_to_zero(self) -> None:
        # Trigger multiple penalties
        actual = [{"x": 9}]
        expected = [{"a": 1, "b": 2}, {"a": 3, "b": 4}]
        m = MetricsCalculator.calculate_result_correctness(actual, expected)
        assert m.score >= 0.0

    def test_none_values_match(self) -> None:
        actual = [{"a": None}]
        expected = [{"a": None}]
        m = MetricsCalculator.calculate_result_correctness(actual, expected)
        assert m.values_match is True

    def test_none_vs_value_mismatch(self) -> None:
        actual = [{"a": None}]
        expected = [{"a": 1}]
        m = MetricsCalculator.calculate_result_correctness(actual, expected)
        assert m.values_match is False


# ---------------------------------------------------------------------------
# MetricsCalculator.calculate_confidence_calibration
# ---------------------------------------------------------------------------


class TestConfidenceCalibration:
    def test_perfect_calibration(self) -> None:
        c = MetricsCalculator.calculate_confidence_calibration(0.9, 0.9)
        assert c.calibration_error == pytest.approx(0.0)
        assert c.is_calibrated is True

    def test_within_threshold(self) -> None:
        c = MetricsCalculator.calculate_confidence_calibration(0.9, 0.87)
        assert c.is_calibrated is True

    def test_outside_threshold(self) -> None:
        c = MetricsCalculator.calculate_confidence_calibration(0.9, 0.7)
        assert c.is_calibrated is False
        assert c.calibration_error > 0.05

    def test_calibration_error_is_absolute(self) -> None:
        c1 = MetricsCalculator.calculate_confidence_calibration(0.8, 0.6)
        c2 = MetricsCalculator.calculate_confidence_calibration(0.6, 0.8)
        assert c1.calibration_error == pytest.approx(c2.calibration_error)

    def test_custom_threshold(self) -> None:
        c = MetricsCalculator.calculate_confidence_calibration(0.9, 0.8, threshold=0.15)
        assert c.is_calibrated is True


# ---------------------------------------------------------------------------
# EvaluationMetrics properties
# ---------------------------------------------------------------------------


class TestEvaluationMetrics:
    def test_pass_rate(self, sample_metrics: EvaluationMetrics) -> None:
        assert sample_metrics.pass_rate == pytest.approx(0.8)

    def test_fail_rate(self, sample_metrics: EvaluationMetrics) -> None:
        assert sample_metrics.fail_rate == pytest.approx(0.2)

    def test_pass_rate_zero_tests(self) -> None:
        m = EvaluationMetrics(
            total_tests=0,
            passed_tests=0,
            failed_tests=0,
            accuracy=0.0,
            avg_result_correctness=0.0,
            avg_answer_quality=0.0,
            avg_confidence_score=0.0,
            confidence_calibration_error=0.0,
            execution_time_ms=0.0,
        )
        assert m.pass_rate == 0.0

    def test_fail_rate_complements_pass_rate(self, sample_metrics: EvaluationMetrics) -> None:
        assert sample_metrics.pass_rate + sample_metrics.fail_rate == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# AnswerQualityEvaluator
# ---------------------------------------------------------------------------


class TestAnswerQualityEvaluator:
    def test_returns_neutral_when_no_client(self) -> None:
        evaluator = AnswerQualityEvaluator(llm_client=None)
        result = evaluator.evaluate("answer", "expected", [], "question")
        assert result.score == 0.5
        assert "not configured" in result.evaluator_notes

    def test_calls_llm_client_when_provided(self) -> None:
        llm_client = MagicMock()
        llm_client.synthesize_answer.return_value = (
            '{"factual_accuracy": true, "completeness": true, '
            '"relevance": true, "clarity": true, "score": 0.9, "notes": "good"}'
        )
        evaluator = AnswerQualityEvaluator(llm_client=llm_client)
        result = evaluator.evaluate("answer", "expected", [{"n": 1}], "question")
        assert llm_client.synthesize_answer.call_count == 1
        assert result.score == pytest.approx(0.9)
        assert result.factual_accuracy is True

    def test_handles_llm_error_gracefully(self) -> None:
        llm_client = MagicMock()
        llm_client.synthesize_answer.side_effect = RuntimeError("API down")
        evaluator = AnswerQualityEvaluator(llm_client=llm_client)
        result = evaluator.evaluate("a", "e", [], "q")
        assert result.score == 0.0
        assert "Evaluation failed" in result.evaluator_notes

    def test_handles_malformed_json_gracefully(self) -> None:
        llm_client = MagicMock()
        llm_client.synthesize_answer.return_value = "not json at all"
        evaluator = AnswerQualityEvaluator(llm_client=llm_client)
        result = evaluator.evaluate("a", "e", [], "q")
        # Should fall back gracefully
        assert 0.0 <= result.score <= 1.0
