"""Report generation for evaluation results."""

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from nlqe.testing.evaluator import Evaluator, TestCaseResult
from nlqe.testing.metrics import EvaluationMetrics
from nlqe.utils import get_logger

logger = get_logger(__name__)


class ReportGenerator:
    """Generate evaluation reports in multiple formats."""

    @staticmethod
    def generate_json_report(
        evaluator: Evaluator,
        metrics: EvaluationMetrics,
        output_path: str | Path,
    ) -> Path:
        """Generate JSON report with detailed metrics.

        Args:
            evaluator: Evaluator instance with test results
            metrics: EvaluationMetrics from evaluation
            output_path: Path to write report

        Returns:
            Path to generated report
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_tests": metrics.total_tests,
                "passed_tests": metrics.passed_tests,
                "failed_tests": metrics.failed_tests,
                "pass_rate": metrics.pass_rate,
                "accuracy": metrics.accuracy,
                "execution_time_ms": metrics.execution_time_ms,
            },
            "metrics": {
                "avg_result_correctness": metrics.avg_result_correctness,
                "avg_answer_quality": metrics.avg_answer_quality,
                "avg_confidence_score": metrics.avg_confidence_score,
                "confidence_calibration_error": metrics.confidence_calibration_error,
            },
            "by_category": metrics.by_category,
            "by_difficulty": metrics.by_difficulty,
            "test_details": [ReportGenerator._format_test_result(r) for r in evaluator.results],
        }

        with open(output_path, "w") as f:
            json.dump(report, f, indent=2, default=str)

        logger.info(f"JSON report written to {output_path}")
        return output_path

    @staticmethod
    def generate_csv_report(
        evaluator: Evaluator,
        output_path: str | Path,
    ) -> Path:
        """Generate CSV report with per-test results.

        Args:
            evaluator: Evaluator instance with test results
            output_path: Path to write report

        Returns:
            Path to generated report
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        fieldnames = [
            "test_id",
            "category",
            "difficulty",
            "status",
            "result_correctness_score",
            "answer_quality_score",
            "confidence_score",
            "calibration_error",
            "execution_time_ms",
            "error",
        ]

        with open(output_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for result in evaluator.results:
                writer.writerow(
                    {
                        "test_id": result.test_case.id,
                        "category": result.test_case.category,
                        "difficulty": result.test_case.difficulty,
                        "status": "PASS" if result.success else "FAIL",
                        "result_correctness_score": (
                            result.result_correctness.score if result.result_correctness else ""
                        ),
                        "answer_quality_score": (
                            result.answer_quality.score if result.answer_quality else ""
                        ),
                        "confidence_score": (
                            result.confidence_calibration.predicted_confidence
                            if result.confidence_calibration
                            else ""
                        ),
                        "calibration_error": (
                            result.confidence_calibration.calibration_error
                            if result.confidence_calibration
                            else ""
                        ),
                        "execution_time_ms": result.execution_time_ms,
                        "error": result.error or "",
                    }
                )

        logger.info(f"CSV report written to {output_path}")
        return output_path

    @staticmethod
    def generate_markdown_report(
        evaluator: Evaluator,
        metrics: EvaluationMetrics,
        output_path: str | Path,
    ) -> Path:
        """Generate human-readable markdown report.

        Args:
            evaluator: Evaluator instance with test results
            metrics: EvaluationMetrics from evaluation
            output_path: Path to write report

        Returns:
            Path to generated report
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        lines: list[str] = []

        # Header
        lines.append("# NLQE Evaluation Report")
        lines.append("")
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")

        # Summary
        lines.append("## Summary")
        lines.append("")
        lines.append(f"- **Total Tests**: {metrics.total_tests}")
        lines.append(f"- **Passed**: {metrics.passed_tests}")
        lines.append(f"- **Failed**: {metrics.failed_tests}")
        lines.append(f"- **Pass Rate**: {metrics.pass_rate:.1%}")
        lines.append(f"- **Accuracy**: {metrics.accuracy:.1%}")
        lines.append(f"- **Execution Time**: {metrics.execution_time_ms:.2f}ms")
        lines.append("")

        # Metrics
        lines.append("## Metrics")
        lines.append("")
        lines.append("|Metric|Value|")
        lines.append("|---|---|")
        lines.append(f"|Average Result Correctness|{metrics.avg_result_correctness:.2%}|")
        lines.append(f"|Average Answer Quality|{metrics.avg_answer_quality:.2%}|")
        lines.append(f"|Average Confidence Score|{metrics.avg_confidence_score:.2%}|")
        lines.append(f"|Confidence Calibration Error|{metrics.confidence_calibration_error:.4f}|")
        lines.append("")

        # By Category
        lines.append("## Results by Category")
        lines.append("")
        lines.append("|Category|Total|Passed|Avg Correctness|")
        lines.append("|---|---|---|---|")
        for category in sorted(metrics.by_category.keys()):
            cat_data = metrics.by_category[category]
            passed = cat_data["passed"]
            total = cat_data["total"]
            avg_corr = cat_data["avg_correctness"]
            lines.append(f"|{category}|{total}|{passed}|{avg_corr:.2%}|")
        lines.append("")

        # By Difficulty
        lines.append("## Results by Difficulty")
        lines.append("")
        lines.append("|Difficulty|Total|Passed|Avg Correctness|")
        lines.append("|---|---|---|---|")
        for difficulty in ["easy", "medium", "hard"]:
            if difficulty in metrics.by_difficulty:
                diff_data = metrics.by_difficulty[difficulty]
                passed = diff_data["passed"]
                total = diff_data["total"]
                avg_corr = diff_data["avg_correctness"]
                lines.append(f"|{difficulty.capitalize()}|{total}|{passed}|{avg_corr:.2%}|")
        lines.append("")

        # Failed Tests
        failed_tests = evaluator.get_failed_tests()
        if failed_tests:
            lines.append("## Failed Tests")
            lines.append("")
            for result in failed_tests:
                lines.append(f"### {result.test_case.id}")
                lines.append(f"- **Category**: {result.test_case.category}")
                lines.append(f"- **Difficulty**: {result.test_case.difficulty}")
                lines.append(f"- **Description**: {result.test_case.description}")
                if result.result_correctness:
                    lines.append(f"- **Result Correctness**: {result.result_correctness.score:.2%}")
                    if result.result_correctness.issues:
                        lines.append("  - Issues:")
                        for issue in result.result_correctness.issues:
                            lines.append(f"    - {issue}")
                if result.answer_quality:
                    lines.append(f"- **Answer Quality**: {result.answer_quality.score:.2%}")
                if result.error:
                    lines.append(f"- **Error**: {result.error}")
                lines.append("")
            lines.append("")

        with open(output_path, "w") as f:
            f.write("\n".join(lines))

        logger.info(f"Markdown report written to {output_path}")
        return output_path

    @staticmethod
    def _format_test_result(result: TestCaseResult) -> dict[str, Any]:
        """Format test result for JSON serialization.

        Args:
            result: TestCaseResult instance

        Returns:
            Dictionary with formatted result data
        """
        return {
            "test_id": result.test_case.id,
            "category": result.test_case.category,
            "difficulty": result.test_case.difficulty,
            "status": "PASS" if result.success else "FAIL",
            "description": result.test_case.description,
            "generated_sql": result.generated_sql,
            "actual_rows": len(result.actual_results),
            "expected_rows": len(result.test_case.expected_results),
            "result_correctness": (
                {
                    "score": result.result_correctness.score,
                    "row_count_match": result.result_correctness.row_count_match,
                    "columns_match": result.result_correctness.columns_match,
                    "values_match": result.result_correctness.values_match,
                    "issues": result.result_correctness.issues,
                }
                if result.result_correctness
                else None
            ),
            "answer_quality": (
                {
                    "score": result.answer_quality.score,
                    "factual_accuracy": result.answer_quality.factual_accuracy,
                    "completeness": result.answer_quality.completeness,
                    "relevance": result.answer_quality.relevance,
                    "clarity": result.answer_quality.clarity,
                    "notes": result.answer_quality.evaluator_notes,
                }
                if result.answer_quality
                else None
            ),
            "confidence": (
                {
                    "predicted": result.confidence_calibration.predicted_confidence,
                    "actual": result.confidence_calibration.actual_accuracy,
                    "calibration_error": result.confidence_calibration.calibration_error,
                    "is_calibrated": result.confidence_calibration.is_calibrated,
                }
                if result.confidence_calibration
                else None
            ),
            "execution_time_ms": result.execution_time_ms,
            "error": result.error,
        }
