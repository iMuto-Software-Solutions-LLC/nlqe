"""DuckDB query execution."""

import re
import time
from typing import Any

import duckdb

from nlqe.types import DatabaseConfig, MSSQLConfig, MySQLConfig, PostgresConfig, SQLValidationResult
from nlqe.utils import (
    QueryTimeoutError,
    SQLSafetyError,
    SQLSchemaError,
    SQLSyntaxError,
    get_logger,
    is_remote_path,
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

    def __init__(self, datasource_path: str | DatabaseConfig) -> None:
        """Initialize executor.

        Args:
            datasource_path: Path to datasource file or external database configuration
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
            import os

            if (
                isinstance(self.datasource_path, str)
                and os.path.isfile(self.datasource_path)
                and self.datasource_path.endswith(".duckdb")
            ):
                self._connection = duckdb.connect(self.datasource_path)
            else:
                self._connection = duckdb.connect(":memory:")
                self._setup_datasource()
        return self._connection

    def _setup_datasource(self) -> None:
        """Load datasource into DuckDB."""
        conn = self._connection
        if conn is None:
            raise RuntimeError("Connection not initialized")

        import os

        # Handle external databases
        if isinstance(self.datasource_path, PostgresConfig):
            uri = self.datasource_path.uri
            if not uri:
                raise ValueError(
                    "PostgreSQL URI is not set in configuration or environment (NLQE_POSTGRES_URI)"
                )
            logger.info("Attaching PostgreSQL database via DuckDB extension")
            conn.execute("INSTALL postgres; LOAD postgres;")
            conn.execute(f"ATTACH '{uri}' AS pg (TYPE POSTGRES);")
            self._table_name = "pg"
            return

        if isinstance(self.datasource_path, MySQLConfig):
            uri = self.datasource_path.uri
            if not uri:
                raise ValueError(
                    "MySQL URI is not set in configuration or environment (NLQE_MYSQL_URI)"
                )
            logger.info("Attaching MySQL database via DuckDB extension")
            conn.execute("INSTALL mysql; LOAD mysql;")
            conn.execute(f"ATTACH '{uri}' AS mysql (TYPE MYSQL);")
            self._table_name = "mysql"
            return

        if isinstance(self.datasource_path, MSSQLConfig):
            uri = self.datasource_path.uri
            if not uri:
                raise ValueError(
                    "MSSQL URI is not set in configuration or environment (NLQE_MSSQL_URI)"
                )
            logger.info("Attaching MSSQL database via ODBC extension")
            # Note: The ODBC driver for SQL Server must be installed on the host system.
            conn.execute("INSTALL odbc; LOAD odbc;")
            conn.execute(f"ATTACH '{uri}' AS mssql (TYPE ODBC);")
            self._table_name = "mssql"
            return

        if not isinstance(self.datasource_path, str):
            raise TypeError(f"Unsupported datasource config type: {type(self.datasource_path)}")

        # Handle remote files
        if is_remote_path(self.datasource_path):
            logger.info(f"Loading remote datasource: {self.datasource_path}")
            conn.execute("INSTALL httpfs; LOAD httpfs;")
            
            # Basic cloud configuration from environment
            if "s3://" in self.datasource_path.lower():
                s3_key = os.getenv("AWS_ACCESS_KEY_ID")
                s3_secret = os.getenv("AWS_SECRET_ACCESS_KEY")
                s3_region = os.getenv("AWS_REGION")
                s3_endpoint = os.getenv("AWS_ENDPOINT_URL_S3") or os.getenv("AWS_S3_ENDPOINT")
                
                if s3_key:
                    conn.execute(f"SET s3_access_key_id='{s3_key}'")
                if s3_secret:
                    conn.execute(f"SET s3_secret_access_key='{s3_secret}'")
                if s3_region:
                    conn.execute(f"SET s3_region='{s3_region}'")
                if s3_endpoint:
                    conn.execute(f"SET s3_endpoint='{s3_endpoint.replace('http://', '').replace('https://', '')}'")
                    if "http://" in s3_endpoint.lower():
                        conn.execute("SET s3_use_ssl=false")
            
            self._table_name = os.path.splitext(os.path.basename(self.datasource_path.split('?')[0]))[0]
            conn.execute(f"CREATE TABLE {self._table_name} AS SELECT * FROM '{self.datasource_path}'")
            logger.info(f"Loaded remote datasource into table {self._table_name}")
            return

        if os.path.isdir(self.datasource_path):
            for file in os.listdir(self.datasource_path):
                ext = os.path.splitext(file)[1].lower()
                if ext in [".parquet", ".csv"]:
                    table_name = os.path.splitext(file)[0]
                    file_path = os.path.join(self.datasource_path, file).replace("\\", "/")
                    conn.execute(f"CREATE TABLE {table_name} AS SELECT * FROM '{file_path}'")
            logger.info(f"Loaded directory datasource {self.datasource_path}")
            return

        # Determine table name from file path
        self._table_name = os.path.splitext(os.path.basename(self.datasource_path))[0]
        safe_path = self.datasource_path.replace("\\", "/")

        # Load based on file type
        if self.datasource_path.endswith(".parquet"):
            conn.execute(f"CREATE TABLE {self._table_name} AS SELECT * FROM '{safe_path}'")
            logger.info(f"Loaded parquet datasource into table {self._table_name}")
        elif self.datasource_path.endswith(".csv"):
            conn.execute(f"CREATE TABLE {self._table_name} AS SELECT * FROM '{safe_path}'")
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
            if "not found" in error_msg.lower() or "does not exist" in error_msg.lower():
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
