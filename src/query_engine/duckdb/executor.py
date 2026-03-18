"""DuckDB query execution."""

import re
import time
from typing import Any

import duckdb

from query_engine.types import SQLValidationResult
from query_engine.utils import (
    QueryTimeoutError,
    SQLSafetyError,
    SQLSchemaError,
    SQLSyntaxError,
    get_logger,
)

logger = get_logger(__name__)

# Dangerous SQL operations to block
DANGEROUS_PATTERNS = [
    r"DROP\s+TABLE",
    r"DELETE\s+FROM",
    r"TRUNCATE",
    r"ALTER\s+TABLE",
    r"CREATE\s+TABLE",
    r"INSERT\s+INTO",
    r"UPDATE\s+\w+\s+SET",
]


class DuckDBExecutor:
    """Execute SQL queries safely in DuckDB."""

    def __init__(self, datasource_path: str) -> None:
        """Initialize executor.

        Args:
            datasource_path: Path to datasource file
        """
        self.datasource_path = datasource_path
        self._connection: Any | None = None
        self._table_name: str | None = None

    def _get_connection(self) -> Any:
        """Get or create DuckDB connection.

        Returns:
            DuckDB connection
        """
        if self._connection is None:
            self._connection = duckdb.connect(":memory:")
            self._setup_datasource()
        return self._connection

    def _setup_datasource(self) -> None:
        """Load datasource into DuckDB."""
        conn = self._connection
        if conn is None:
            raise RuntimeError("Connection not initialized")

        # Determine table name from file path
        import os

        self._table_name = os.path.splitext(os.path.basename(self.datasource_path))[0]

        # Load based on file type
        if self.datasource_path.endswith(".parquet"):
            conn.execute(
                f"CREATE TABLE {self._table_name} AS SELECT * FROM '{self.datasource_path}'"
            )
            logger.info(f"Loaded parquet datasource into table {self._table_name}")
        elif self.datasource_path.endswith(".csv"):
            conn.execute(
                f"CREATE TABLE {self._table_name} AS SELECT * FROM '{self.datasource_path}'"
            )
            logger.info(f"Loaded CSV datasource into table {self._table_name}")
        else:
            raise RuntimeError(f"Unsupported datasource format: {self.datasource_path}")

    def validate_sql(self, sql: str) -> SQLValidationResult:
        """Validate SQL before execution.

        Args:
            sql: SQL query to validate

        Returns:
            SQLValidationResult
        """
        issues: list[str] = []

        # Check for dangerous operations
        sql_upper = sql.upper()
        for pattern in DANGEROUS_PATTERNS:
            if re.search(pattern, sql_upper):
                issues.append(f"Dangerous operation detected: {pattern}")

        # Check for multiple statements
        statements = [s.strip() for s in sql.split(";") if s.strip()]
        if len(statements) > 1:
            issues.append("Multiple SQL statements not allowed")

        # Try to parse the query
        try:
            conn = self._get_connection()
            # Use EXPLAIN to validate without executing
            conn.execute(f"EXPLAIN {sql}")
        except Exception as e:
            error_msg = str(e)
            if "not found" in error_msg.lower():
                issues.append(f"Schema error: {error_msg}")
            else:
                issues.append(f"SQL syntax error: {error_msg}")

        return SQLValidationResult(
            is_valid=len(issues) == 0,
            issues=issues,
            error_message="; ".join(issues) if issues else None,
        )

    def execute(
        self, sql: str, timeout_seconds: int = 30
    ) -> tuple[bool, list[dict[str, Any]] | str]:
        """Execute SQL query safely.

        Args:
            sql: SQL query to execute
            timeout_seconds: Query timeout in seconds

        Returns:
            Tuple of (success: bool, data: list[dict] or error: str)

        Raises:
            SQLSyntaxError: If SQL has syntax errors
            SQLSchemaError: If SQL references non-existent tables/columns
            SQLSafetyError: If SQL contains dangerous operations
            QueryTimeoutError: If query exceeds timeout
        """
        # Validate first
        validation = self.validate_sql(sql)
        if not validation.is_valid:
            for issue in validation.issues:
                if "Schema error" in issue:
                    raise SQLSchemaError(issue)
                elif "Dangerous operation" in issue:
                    raise SQLSafetyError(issue)
                elif "SQL syntax error" in issue:
                    raise SQLSyntaxError(issue)

        # Execute query
        logger.info(f"Executing SQL: {sql[:100]}...")
        start_time = time.time()

        try:
            conn = self._get_connection()

            # Set timeout (DuckDB doesn't have native timeout, so we'll implement basic check)
            result = conn.execute(sql).fetchall()

            elapsed = time.time() - start_time
            if elapsed > timeout_seconds:
                raise QueryTimeoutError(
                    f"Query exceeded timeout of {timeout_seconds}s (took {elapsed:.1f}s)"
                )

            # Convert to list of dicts
            description = conn.description
            if not description:
                return True, []

            columns = [col[0] for col in description]
            data = [dict(zip(columns, row)) for row in result]

            logger.info(f"Query executed successfully in {elapsed:.2f}s ({len(data)} rows)")
            return True, data

        except (SQLSyntaxError, SQLSchemaError, SQLSafetyError, QueryTimeoutError):
            raise
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Query execution failed: {error_msg}")
            raise SQLSyntaxError(f"Query execution failed: {error_msg}") from e

    def close(self) -> None:
        """Close database connection."""
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    def __del__(self) -> None:
        """Ensure connection is closed."""
        self.close()
