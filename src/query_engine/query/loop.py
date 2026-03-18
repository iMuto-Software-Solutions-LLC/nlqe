"""Query execution loop with automatic SQL debugging."""

import time
from typing import Any

from query_engine.duckdb.executor import DuckDBExecutor
from query_engine.llm.client import LLMClient
from query_engine.types import DebugInfo, QueryResponse
from query_engine.utils import (
    DebugFailedError,
    QueryExecutionError,
    SQLSchemaError,
    SQLSyntaxError,
    get_logger,
)

logger = get_logger(__name__)


class QueryLoop:
    """Execute a query end-to-end: generate SQL → execute → debug → synthesise."""

    def __init__(
        self,
        llm_client: LLMClient,
        duckdb_executor: DuckDBExecutor,
        max_debug_attempts: int = 3,
    ) -> None:
        """Initialise.

        Args:
            llm_client: Provider-agnostic ``LLMClient``.
            duckdb_executor: ``DuckDBExecutor`` for running SQL.
            max_debug_attempts: Total execution attempts including the first.
        """
        self.llm_client = llm_client
        self.duckdb_executor = duckdb_executor
        self.max_debug_attempts = max_debug_attempts

    def execute(
        self, user_query: str, context: str, query_timeout_seconds: int = 30
    ) -> QueryResponse:
        """Execute a user query end-to-end.

        Pipeline:
        1. Generate SQL via LLM.
        2. Execute SQL in DuckDB; if it fails, ask the LLM to debug and retry
           (up to ``max_debug_attempts`` total attempts).
        3. Synthesise a natural-language answer from the results.
        4. Compute a confidence score.

        Args:
            user_query: Natural language question.
            context: Markdown schema + optional few-shot context.
            query_timeout_seconds: DuckDB execution timeout.

        Returns:
            ``QueryResponse`` containing SQL, data, answer, and metadata.

        Raises:
            DebugFailedError: If all execution attempts are exhausted.
        """
        start_time = time.time()
        logger.info(f"Executing query: {user_query!r}")

        # Step 1 — Generate SQL
        generated_sql = self.llm_client.generate_sql(context, user_query)

        # Step 2 — Execute with debug loop
        debug_info: DebugInfo | None = None
        query_results: list[dict[str, Any]] = []
        error_message: str | None = None

        success, result, debug_attempts_used = self._execute_with_debug(
            generated_sql, user_query, context, query_timeout_seconds
        )

        if success:
            query_results = result  # type: ignore[assignment]
            if debug_attempts_used > 0:
                debug_info = DebugInfo(
                    attempts=debug_attempts_used,
                    errors=[],
                    modified_sqls=[],
                    first_error="",
                    final_error=None,
                )
        else:
            error_message = result  # type: ignore[assignment]
            debug_info = DebugInfo(
                attempts=self.max_debug_attempts,
                errors=[error_message] if error_message else [],
                modified_sqls=[],
                first_error=error_message or "Unknown error",
                final_error=error_message,
            )

        if error_message:
            execution_time_ms = (time.time() - start_time) * 1000
            logger.error(f"Query failed after {self.max_debug_attempts} attempts")
            raise DebugFailedError(f"Query failed: {error_message}")

        # Step 3 — Synthesise answer
        execution_time_ms = (time.time() - start_time) * 1000
        try:
            answer = self.llm_client.synthesize_answer(
                query_results or [], user_query, execution_time_ms
            )
        except Exception as e:
            logger.error(f"Answer synthesis failed: {e}")
            answer = f"Query succeeded with {len(query_results or [])} results"

        # Step 4 — Confidence score
        confidence = self._calculate_confidence(query_results or [], debug_info, execution_time_ms)

        return QueryResponse(
            user_query=user_query,
            generated_sql=generated_sql,
            data=query_results or [],
            answer=answer,
            confidence_score=confidence,
            execution_time_ms=execution_time_ms,
            result_rows=len(query_results or []),
            debug_info=debug_info,
            error=None,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _execute_with_debug(
        self,
        initial_sql: str,
        user_query: str,
        context: str,
        query_timeout_seconds: int,
    ) -> tuple[bool, list[dict[str, Any]] | str, int]:
        """Try executing SQL, asking the LLM to fix it on each failure.

        Returns:
            ``(success, results_or_error, debug_attempts_used)`` where
            *debug_attempts_used* is the number of debug (repair) calls made.
        """
        current_sql = initial_sql
        debug_attempts_used = 0

        for attempt in range(1, self.max_debug_attempts + 1):
            logger.info(f"Execution attempt {attempt}/{self.max_debug_attempts}")

            try:
                success, result = self.duckdb_executor.execute(
                    current_sql, timeout_seconds=query_timeout_seconds
                )
                if success:
                    logger.info(f"Query succeeded on attempt {attempt}")
                    return True, result, debug_attempts_used

            except (SQLSyntaxError, SQLSchemaError) as e:
                error_msg = str(e)
                logger.warning(f"Query failed (attempt {attempt}): {error_msg}")

                if attempt < self.max_debug_attempts:
                    try:
                        current_sql = self.llm_client.debug_sql(
                            context, current_sql, error_msg, attempt
                        )
                        debug_attempts_used += 1
                        logger.info(f"Debug fix generated: {current_sql[:80]}...")
                    except Exception as debug_err:
                        logger.error(f"Debug request failed: {debug_err}")
                        return False, f"Query failed: {error_msg}", debug_attempts_used
                else:
                    return (
                        False,
                        f"Query failed after {self.max_debug_attempts} attempts: {error_msg}",
                        debug_attempts_used,
                    )

            except QueryExecutionError as e:
                logger.error(f"Unrecoverable execution error: {e}")
                return False, str(e), debug_attempts_used

        return False, "Query execution exhausted all attempts", debug_attempts_used

    @staticmethod
    def _calculate_confidence(
        results: list[dict[str, Any]],
        debug_info: DebugInfo | None,
        execution_time_ms: float,
    ) -> float:
        """Heuristic confidence score in [0, 1].

        Deductions:
        - 0.10 per debug attempt used (max three).
        - 0.10 if the query returned no rows.
        - 0.05 if execution took > 5 seconds.
        """
        confidence = 1.0
        if debug_info and debug_info.attempts > 0:
            confidence -= 0.1 * min(debug_info.attempts, 3)
        if not results:
            confidence -= 0.1
        if execution_time_ms > 5000:
            confidence -= 0.05
        return max(0.0, min(1.0, confidence))
