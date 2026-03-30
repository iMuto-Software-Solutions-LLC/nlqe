"""Evaluation pipeline for query engine accuracy and quality."""

import time
from dataclasses import dataclass, field
from typing import Any

from nlqe.engine import QueryEngine
from nlqe.testing.datasets import GoldenDataset, GoldenTestCase
from nlqe.testing.metrics import (
    AnswerQualityEvaluator,
    AnswerQualityMetric,
    ConfidenceCalibration,
    EvaluationMetrics,
    MetricsCalculator,
    ResultCorrectnessMetric,
)
from nlqe.utils import get_logger

logger = get_logger(__name__)


@dataclass
class TestCaseResult:
    """Result of evaluating a single test case."""

    test_case: GoldenTestCase
    success: bool
    generated_sql: str | None = None
    actual_results: list[dict[str, Any]] = field(default_factory=list)
    result_correctness: ResultCorrectnessMetric | None = None
    answer_quality: AnswerQualityMetric | None = None
    confidence_calibration: ConfidenceCalibration | None = None
    error: str | None = None
    execution_time_ms: float = 0.0


class Evaluator:
    """Orchestrate evaluation of query engine against golden dataset."""

    def __init__(
        self,
        query_engine: QueryEngine,
        golden_dataset: GoldenDataset,
        answer_quality_evaluator: AnswerQualityEvaluator | None = None,
    ):
        """Initialize evaluator.

        Args:
            query_engine: QueryEngine instance to evaluate
            golden_dataset: Golden dataset with test cases
            answer_quality_evaluator: Optional custom answer quality evaluator
        """
        self.query_engine = query_engine
        self.golden_dataset = golden_dataset
        self.answer_quality_evaluator = answer_quality_evaluator or AnswerQualityEvaluator()
        self.results: list[TestCaseResult] = []

    def evaluate_all(self) -> EvaluationMetrics:
        """Evaluate all test cases in golden dataset.

        Returns:
            EvaluationMetrics with aggregated results
        """
        logger.info(f"Starting evaluation of {self.golden_dataset.count} test cases")

        start_time = time.time()
        self.results = []

        # Evaluate each test case
        for test_case in self.golden_dataset.datasets:
            result = self._evaluate_single(test_case)
            self.results.append(result)
            logger.debug(f"Test {test_case.id}: {'PASS' if result.success else 'FAIL'}")

        total_time_ms = (time.time() - start_time) * 1000

        # Calculate aggregated metrics
        metrics = self._calculate_metrics(total_time_ms)

        logger.info(f"Evaluation complete. Pass rate: {metrics.pass_rate:.0%}")

        return metrics

    def evaluate_by_category(self, category: str) -> EvaluationMetrics:
        """Evaluate test cases in a specific category.

        Args:
            category: Category name

        Returns:
            EvaluationMetrics for that category
        """
        test_cases = self.golden_dataset.get_by_category(category)
        logger.info(f"Evaluating {len(test_cases)} test cases in category: {category}")

        start_time = time.time()
        results = []

        for test_case in test_cases:
            result = self._evaluate_single(test_case)
            results.append(result)

        total_time_ms = (time.time() - start_time) * 1000

        # Temporarily replace results for metrics calculation
        original_results = self.results
        self.results = results
        metrics = self._calculate_metrics(total_time_ms)
        self.results = original_results

        return metrics

    def evaluate_by_difficulty(self, difficulty: str) -> EvaluationMetrics:
        """Evaluate test cases of a specific difficulty level.

        Args:
            difficulty: Difficulty level (easy, medium, hard)

        Returns:
            EvaluationMetrics for that difficulty
        """
        test_cases = self.golden_dataset.get_by_difficulty(difficulty)
        logger.info(f"Evaluating {len(test_cases)} test cases with difficulty: {difficulty}")

        start_time = time.time()
        results = []

        for test_case in test_cases:
            result = self._evaluate_single(test_case)
            results.append(result)

        total_time_ms = (time.time() - start_time) * 1000

        # Temporarily replace results for metrics calculation
        original_results = self.results
        self.results = results
        metrics = self._calculate_metrics(total_time_ms)
        self.results = original_results

        return metrics

    def _evaluate_single(self, test_case: GoldenTestCase) -> TestCaseResult:
        """Evaluate a single test case.

        Args:
            test_case: Test case to evaluate

        Returns:
            TestCaseResult with evaluation details
        """
        result = TestCaseResult(test_case=test_case, success=False)

        try:
            start_time = time.time()

            # Execute query
            query_response = self.query_engine.query(test_case.user_query)

            result.execution_time_ms = (time.time() - start_time) * 1000
            result.generated_sql = query_response.generated_sql
            result.actual_results = query_response.data

            # Calculate result correctness
            result.result_correctness = MetricsCalculator.calculate_result_correctness(
                actual_results=query_response.data,
                expected_results=test_case.expected_results,
                acceptable_variance=test_case.acceptable_variance,
            )

            # Evaluate answer quality
            result.answer_quality = self.answer_quality_evaluator.evaluate(
                generated_answer=query_response.answer,
                expected_answer=test_case.expected_answer_summary,
                query_results=query_response.data,
                user_question=test_case.user_query,
            )

            # Calculate confidence calibration
            actual_accuracy = (result.result_correctness.score + result.answer_quality.score) / 2
            result.confidence_calibration = MetricsCalculator.calculate_confidence_calibration(
                predicted_confidence=query_response.confidence_score,
                actual_accuracy=actual_accuracy,
            )

            # Consider test passed if result is correct and answer quality is good
            result.success = (
                result.result_correctness.score >= 0.8 and result.answer_quality.score >= 0.7
            )

        except Exception as e:
            result.error = str(e)
            logger.error(f"Error evaluating test case {test_case.id}: {e}")

        return result

    def _calculate_metrics(self, total_time_ms: float) -> EvaluationMetrics:
        """Calculate aggregated metrics from results.

        Args:
            total_time_ms: Total evaluation time in milliseconds

        Returns:
            EvaluationMetrics with aggregated results
        """
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.success)
        failed_tests = total_tests - passed_tests

        # Calculate averages
        correctness_scores = [
            r.result_correctness.score for r in self.results if r.result_correctness is not None
        ]
        quality_scores = [
            r.answer_quality.score for r in self.results if r.answer_quality is not None
        ]
        confidence_scores = [
            r.confidence_calibration.predicted_confidence
            for r in self.results
            if r.confidence_calibration is not None
        ]
        calibration_errors = [
            r.confidence_calibration.calibration_error
            for r in self.results
            if r.confidence_calibration is not None
        ]

        avg_result_correctness = (
            sum(correctness_scores) / len(correctness_scores) if correctness_scores else 0.0
        )
        avg_answer_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
        avg_confidence_score = (
            sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
        )
        avg_calibration_error = (
            sum(calibration_errors) / len(calibration_errors) if calibration_errors else 0.0
        )

        # Group by category and difficulty
        by_category: dict[str, dict[str, Any]] = {}
        by_difficulty: dict[str, dict[str, Any]] = {}

        for category in self.golden_dataset.categories:
            category_results = [r for r in self.results if r.test_case.category == category]
            by_category[category] = {
                "total": len(category_results),
                "passed": sum(1 for r in category_results if r.success),
                "avg_correctness": (
                    sum(
                        r.result_correctness.score
                        for r in category_results
                        if r.result_correctness is not None
                    )
                    / len([r for r in category_results if r.result_correctness is not None])
                    if [r for r in category_results if r.result_correctness is not None]
                    else 0.0
                ),
            }

        for difficulty in self.golden_dataset.difficulties:
            difficulty_results = [r for r in self.results if r.test_case.difficulty == difficulty]
            by_difficulty[difficulty] = {
                "total": len(difficulty_results),
                "passed": sum(1 for r in difficulty_results if r.success),
                "avg_correctness": (
                    sum(
                        r.result_correctness.score
                        for r in difficulty_results
                        if r.result_correctness is not None
                    )
                    / len([r for r in difficulty_results if r.result_correctness is not None])
                    if [r for r in difficulty_results if r.result_correctness is not None]
                    else 0.0
                ),
            }

        return EvaluationMetrics(
            total_tests=total_tests,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            accuracy=passed_tests / total_tests if total_tests > 0 else 0.0,
            avg_result_correctness=avg_result_correctness,
            avg_answer_quality=avg_answer_quality,
            avg_confidence_score=avg_confidence_score,
            confidence_calibration_error=avg_calibration_error,
            execution_time_ms=total_time_ms,
            by_category=by_category,
            by_difficulty=by_difficulty,
        )

    def get_failed_tests(self) -> list[TestCaseResult]:
        """Get all failed test cases.

        Returns:
            List of failed TestCaseResult instances
        """
        return [r for r in self.results if not r.success]

    def get_results_by_category(self, category: str) -> list[TestCaseResult]:
        """Get test results for a specific category.

        Args:
            category: Category name

        Returns:
            List of TestCaseResult instances for that category
        """
        return [r for r in self.results if r.test_case.category == category]

    def get_results_by_difficulty(self, difficulty: str) -> list[TestCaseResult]:
        """Get test results for a specific difficulty level.

        Args:
            difficulty: Difficulty level

        Returns:
            List of TestCaseResult instances for that difficulty
        """
        return [r for r in self.results if r.test_case.difficulty == difficulty]
