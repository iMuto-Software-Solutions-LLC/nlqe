"""Accuracy and quality metric calculations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from query_engine.llm.client import LLMClient


class ResultCorrectnessMetric(BaseModel):
    """Result correctness score and details."""

    score: float = Field(ge=0.0, le=1.0)
    row_count_match: bool
    columns_match: bool
    values_match: bool
    issues: list[str] = Field(default_factory=list)


class AnswerQualityMetric(BaseModel):
    """Answer quality evaluation."""

    score: float = Field(ge=0.0, le=1.0)
    factual_accuracy: bool
    completeness: bool
    relevance: bool
    clarity: bool
    evaluator_notes: str = ""


class ConfidenceCalibration(BaseModel):
    """Confidence score calibration metrics."""

    actual_accuracy: float = Field(ge=0.0, le=1.0)
    predicted_confidence: float = Field(ge=0.0, le=1.0)
    calibration_error: float = Field(ge=0.0)
    is_calibrated: bool


class AnswerQualityEvaluator:
    """Evaluate answer quality using an LLM as judge.

    Uses the same ``LLMClient`` abstraction as the rest of the system, so it
    works with any provider (OpenAI, Anthropic, etc.).
    """

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        """Initialise evaluator.

        Args:
            llm_client: Pre-configured ``LLMClient``.  When ``None`` the
                evaluator returns a neutral 0.5 score without calling an LLM
                (useful in unit tests).
        """
        self.llm_client = llm_client

    def evaluate(
        self,
        generated_answer: str,
        expected_answer: str,
        query_results: list[dict[str, Any]],
        user_question: str,
    ) -> AnswerQualityMetric:
        """Evaluate answer quality.

        Args:
            generated_answer: Answer produced by the system.
            expected_answer: Reference answer from the golden dataset.
            query_results: Raw DuckDB results.
            user_question: Original user question.

        Returns:
            ``AnswerQualityMetric`` with per-dimension scores.
        """
        if self.llm_client is None:
            return AnswerQualityMetric(
                score=0.5,
                factual_accuracy=False,
                completeness=False,
                relevance=False,
                clarity=False,
                evaluator_notes="LLM client not configured",
            )

        prompt = self._build_evaluation_prompt(
            user_question, generated_answer, expected_answer, query_results
        )

        try:
            # Reuse the synthesis chain — it returns a plain string which we parse as JSON
            evaluation_text = self.llm_client.synthesize_answer(
                query_results=[{"evaluation_prompt": prompt}],
                user_query=prompt,
                execution_time_ms=0.0,
            )
            return self._parse_evaluation(evaluation_text)
        except Exception as e:
            return AnswerQualityMetric(
                score=0.0,
                factual_accuracy=False,
                completeness=False,
                relevance=False,
                clarity=False,
                evaluator_notes=f"Evaluation failed: {e}",
            )

    def _build_evaluation_prompt(
        self,
        user_question: str,
        generated_answer: str,
        expected_answer: str,
        query_results: list[dict[str, Any]],
    ) -> str:
        """Build evaluation prompt for OpenAI.

        Args:
            user_question: Original user question
            generated_answer: Generated answer
            expected_answer: Expected answer
            query_results: Query results

        Returns:
            Formatted prompt string
        """
        results_summary = f"Data returned {len(query_results)} rows"
        if query_results:
            results_summary += f" with columns: {', '.join(query_results[0].keys())}"

        return f"""Evaluate the following generated answer to a user's question:

USER QUESTION: {user_question}

GENERATED ANSWER: {generated_answer}

EXPECTED ANSWER (reference): {expected_answer}

QUERY RESULTS: {results_summary}

Please evaluate on these criteria:
1. Factual Accuracy: Does the answer correctly reflect the data?
2. Completeness: Does the answer fully address the user's question?
3. Relevance: Is all information in the answer relevant to the question?
4. Clarity: Is the answer clear and well-structured?

Respond in this exact JSON format:
{{
  "factual_accuracy": true/false,
  "completeness": true/false,
  "relevance": true/false,
  "clarity": true/false,
  "score": 0.0-1.0,
  "notes": "brief explanation"
}}"""

    def _parse_evaluation(self, evaluation_text: str) -> AnswerQualityMetric:
        """Parse evaluation response from OpenAI.

        Args:
            evaluation_text: Response text from OpenAI

        Returns:
            Parsed AnswerQualityMetric

        Raises:
            ValueError: If response cannot be parsed
        """
        import json

        try:
            # Extract JSON from response
            json_start = evaluation_text.find("{")
            json_end = evaluation_text.rfind("}") + 1

            if json_start == -1 or json_end == 0:
                raise ValueError("No JSON found in response")

            json_str = evaluation_text[json_start:json_end]
            data = json.loads(json_str)

            return AnswerQualityMetric(
                score=float(data.get("score", 0.5)),
                factual_accuracy=bool(data.get("factual_accuracy", False)),
                completeness=bool(data.get("completeness", False)),
                relevance=bool(data.get("relevance", False)),
                clarity=bool(data.get("clarity", False)),
                evaluator_notes=str(data.get("notes", "")),
            )
        except Exception as e:
            # Return default metric
            return AnswerQualityMetric(
                score=0.5,
                factual_accuracy=False,
                completeness=False,
                relevance=False,
                clarity=False,
                evaluator_notes=f"Parse error: {e!s}",
            )


class MetricsCalculator:
    """Calculate accuracy and quality metrics."""

    @staticmethod
    def calculate_result_correctness(
        actual_results: list[dict[str, Any]],
        expected_results: list[dict[str, Any]],
        acceptable_variance: float = 0.0,
    ) -> ResultCorrectnessMetric:
        """Calculate result correctness score.

        Args:
            actual_results: Results from query execution
            expected_results: Expected reference results
            acceptable_variance: Acceptable variance for numeric values (0.0-1.0)

        Returns:
            ResultCorrectnessMetric with score and details
        """
        issues: list[str] = []
        score = 1.0

        # Check row count
        row_count_match = len(actual_results) == len(expected_results)
        if not row_count_match:
            issues.append(
                f"Row count mismatch: expected {len(expected_results)}, got {len(actual_results)}"
            )
            score -= 0.2

        # Check column names
        if actual_results and expected_results:
            actual_cols = set(actual_results[0].keys())
            expected_cols = set(expected_results[0].keys())
            columns_match = actual_cols == expected_cols

            if not columns_match:
                missing = expected_cols - actual_cols
                extra = actual_cols - expected_cols
                if missing:
                    issues.append(f"Missing columns: {missing}")
                if extra:
                    issues.append(f"Extra columns: {extra}")
                score -= 0.2
        else:
            columns_match = True

        # Check values
        values_match = MetricsCalculator._check_values_match(
            actual_results, expected_results, acceptable_variance
        )

        if not values_match:
            issues.append("Data values don't match")
            # Calculate percentage of mismatched rows
            if actual_results and expected_results:
                mismatched = len(actual_results) != len(expected_results)
                if not mismatched:
                    # Check individual rows
                    mismatch_count = 0
                    for actual, expected in zip(actual_results, expected_results):
                        if not MetricsCalculator._rows_equal(actual, expected, acceptable_variance):
                            mismatch_count += 1
                    mismatch_pct = mismatch_count / len(actual_results)
                    score -= 0.1 * mismatch_pct

        # Clamp score
        score = max(0.0, min(1.0, score))

        return ResultCorrectnessMetric(
            score=score,
            row_count_match=row_count_match,
            columns_match=columns_match,
            values_match=values_match,
            issues=issues,
        )

    @staticmethod
    def _check_values_match(
        actual: list[dict[str, Any]],
        expected: list[dict[str, Any]],
        variance: float,
    ) -> bool:
        """Check if all values match within tolerance."""
        if len(actual) != len(expected):
            return False

        for actual_row, expected_row in zip(actual, expected):
            if not MetricsCalculator._rows_equal(actual_row, expected_row, variance):
                return False

        return True

    @staticmethod
    def _rows_equal(actual: dict[str, Any], expected: dict[str, Any], variance: float) -> bool:
        """Check if two rows are equal within tolerance."""
        if set(actual.keys()) != set(expected.keys()):
            return False

        for key in expected.keys():
            actual_val = actual.get(key)
            expected_val = expected.get(key)

            # Check None/NULL values
            if actual_val is None or expected_val is None:
                if actual_val != expected_val:
                    return False
            # Check numeric with variance
            elif isinstance(expected_val, (int, float)) and isinstance(actual_val, (int, float)):
                if abs(actual_val - expected_val) > expected_val * variance:
                    return False
            # Check exact match for others
            elif actual_val != expected_val:
                return False

        return True

    @staticmethod
    def calculate_confidence_calibration(
        predicted_confidence: float, actual_accuracy: float, threshold: float = 0.05
    ) -> ConfidenceCalibration:
        """Calculate confidence calibration.

        Args:
            predicted_confidence: Confidence score (0.0-1.0)
            actual_accuracy: Actual accuracy (0.0-1.0)
            threshold: Calibration threshold (default 0.05 = 5%)

        Returns:
            ConfidenceCalibration metrics
        """
        calibration_error = abs(predicted_confidence - actual_accuracy)
        is_calibrated = calibration_error <= threshold

        return ConfidenceCalibration(
            actual_accuracy=actual_accuracy,
            predicted_confidence=predicted_confidence,
            calibration_error=calibration_error,
            is_calibrated=is_calibrated,
        )


class EvaluationMetrics(BaseModel):
    """Aggregated evaluation metrics."""

    total_tests: int
    passed_tests: int
    failed_tests: int
    accuracy: float = Field(ge=0.0, le=1.0)
    avg_result_correctness: float = Field(ge=0.0, le=1.0)
    avg_answer_quality: float = Field(ge=0.0, le=1.0)
    avg_confidence_score: float = Field(ge=0.0, le=1.0)
    confidence_calibration_error: float = Field(ge=0.0)
    execution_time_ms: float
    by_category: dict[str, dict[str, Any]] = Field(default_factory=dict)
    by_difficulty: dict[str, dict[str, Any]] = Field(default_factory=dict)

    @property
    def pass_rate(self) -> float:
        """Calculate pass rate percentage."""
        if self.total_tests == 0:
            return 0.0
        return self.passed_tests / self.total_tests

    @property
    def fail_rate(self) -> float:
        """Calculate fail rate percentage."""
        return 1.0 - self.pass_rate
