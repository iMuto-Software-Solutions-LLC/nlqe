import json
import pytest
from unittest.mock import MagicMock

from query_engine.testing.reporter import ReportGenerator
from query_engine.testing.evaluator import Evaluator, TestCaseResult
from query_engine.testing.datasets import GoldenTestCase
from query_engine.testing.metrics import (
    EvaluationMetrics,
    ResultCorrectnessMetric,
    AnswerQualityMetric,
    ConfidenceCalibration,
)

@pytest.fixture
def mock_metrics():
    return EvaluationMetrics(
        total_tests=2,
        passed_tests=1,
        failed_tests=1,
        accuracy=0.5,
        avg_result_correctness=0.8,
        avg_answer_quality=0.75,
        avg_confidence_score=0.9,
        confidence_calibration_error=0.1,
        execution_time_ms=100.0,
        by_category={"cat1": {"total": 2, "passed": 1, "avg_correctness": 0.8}},
        by_difficulty={"easy": {"total": 1, "passed": 1, "avg_correctness": 1.0},
                       "hard": {"total": 1, "passed": 0, "avg_correctness": 0.6}}
    )

@pytest.fixture
def mock_evaluator():
    tc1 = GoldenTestCase(
        id="tc1",
        category="cat1",
        difficulty="easy",
        description="desc1",
        datasource={"type": "parquet", "path": "test"},
        user_query="Q1",
        expected_sql="S1",
        expected_results=[],
        expected_answer_summary="A1"
    )
    tc2 = GoldenTestCase(
        id="tc2",
        category="cat1",
        difficulty="hard",
        description="Failing test",
        datasource={"type": "parquet", "path": "test"},
        user_query="Q2",
        expected_sql="S2",
        expected_results=[],
        expected_answer_summary="A2"
    )
    
    res1 = TestCaseResult(
        test_case=tc1,
        success=True,
        generated_sql="S1",
        actual_results=[],
        result_correctness=ResultCorrectnessMetric(score=1.0, is_correct=True, missing_rows=0, extra_rows=0, mismatched_values=0, row_count_match=True, columns_match=True, values_match=True),
        answer_quality=AnswerQualityMetric(score=1.0, reasoning="Good", factual_accuracy=True, completeness=True, relevance=True, clarity=True),
        confidence_calibration=ConfidenceCalibration(predicted_confidence=0.9, actual_accuracy=0.9, calibration_error=0.0, is_calibrated=True),
        execution_time_ms=10.0
    )
    
    res2 = TestCaseResult(
        test_case=tc2,
        success=False,
        generated_sql="S2",
        actual_results=[],
        result_correctness=ResultCorrectnessMetric(score=0.5, is_correct=False, missing_rows=1, extra_rows=0, mismatched_values=0, issues=["Missing row"], row_count_match=False, columns_match=True, values_match=True),
        answer_quality=AnswerQualityMetric(score=0.5, reasoning="Bad", factual_accuracy=False, completeness=False, relevance=False, clarity=False),
        confidence_calibration=ConfidenceCalibration(predicted_confidence=0.9, actual_accuracy=0.5, calibration_error=0.4, is_calibrated=False),
        error="Some error",
        execution_time_ms=10.0
    )
    
    evaluator = MagicMock(spec=Evaluator)
    evaluator.results = [res1, res2]
    evaluator.get_failed_tests.return_value = [res2]
    return evaluator

def test_generate_json_report(tmp_path, mock_evaluator, mock_metrics):
    output_path = tmp_path / "report.json"
    result_path = ReportGenerator.generate_json_report(mock_evaluator, mock_metrics, output_path)
    
    assert result_path == output_path
    assert output_path.exists()
    
    with open(output_path) as f:
        data = json.load(f)
        assert data["summary"]["total_tests"] == 2
        assert data["summary"]["passed_tests"] == 1
        assert len(data["test_details"]) == 2
        assert data["test_details"][0]["test_id"] == "tc1"
        assert data["test_details"][1]["test_id"] == "tc2"

def test_generate_csv_report(tmp_path, mock_evaluator):
    output_path = tmp_path / "report.csv"
    result_path = ReportGenerator.generate_csv_report(mock_evaluator, output_path)
    
    assert result_path == output_path
    assert output_path.exists()
    
    with open(output_path) as f:
        lines = f.readlines()
        assert len(lines) == 3 # Header + 2 rows
        assert "tc1" in lines[1]
        assert "PASS" in lines[1]
        assert "tc2" in lines[2]
        assert "FAIL" in lines[2]
        assert "Some error" in lines[2]

def test_generate_markdown_report(tmp_path, mock_evaluator, mock_metrics):
    output_path = tmp_path / "report.md"
    result_path = ReportGenerator.generate_markdown_report(mock_evaluator, mock_metrics, output_path)
    
    assert result_path == output_path
    assert output_path.exists()
    
    with open(output_path) as f:
        content = f.read()
        assert "# Query Engine Evaluation Report" in content
        assert "Total Tests**: 2" in content
        assert "Passed**: 1" in content
        assert "|cat1|2|1|80.00%|" in content
        assert "### tc2" in content
        assert "Some error" in content
        assert "Missing row" in content
