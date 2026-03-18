"""Answer synthesis module."""

from typing import Any

from query_engine.utils import get_logger

logger = get_logger(__name__)


class AnswerSynthesizer:
    """Synthesize natural language answers from query results."""

    @staticmethod
    def format_answer(
        answer: str,
        query_results: list[dict[str, Any]],
        execution_time_ms: float,
    ) -> str:
        """Format answer with metadata.

        Args:
            answer: Base answer from OpenAI
            query_results: Query results
            execution_time_ms: Execution time

        Returns:
            Formatted answer
        """
        # Add result count info
        result_info = (
            f"\n\n(Query returned {len(query_results)} results in {execution_time_ms:.0f}ms)"
        )
        return answer + result_info
