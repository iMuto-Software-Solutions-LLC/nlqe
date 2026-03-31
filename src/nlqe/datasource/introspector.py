"""Datasource schema introspection."""

import os
from typing import Any

import duckdb

from nlqe.types import (
    ColumnInfo,
    DatabaseConfig,
    DataSourceSchema,
    DataSourceType,
    MSSQLConfig,
    MySQLConfig,
    PostgresConfig,
    TableInfo,
)
from nlqe.utils import FileNotFoundError, SchemaError, get_logger

logger = get_logger(__name__)


class DataSourceIntrospector:
    """Introspect datasource schemas."""

    def __init__(
        self,
        path: str | DatabaseConfig,
        datasource_type: str | None = None,
        allowlist: list[str] | None = None,
    ) -> None:
        """Initialize introspector.

        Args:
            path: Path to datasource file or config
            datasource_type: Optional type hint (parquet, csv, duckdb)
            allowlist: Optional list of tables to introspect

        Raises:
            FileNotFoundError: If file doesn't exist
            SchemaError: If format is invalid
        """
        if isinstance(path, str) and not os.path.exists(path):
            raise FileNotFoundError(f"Datasource file not found: {path}")

        self.path = path
        self.allowlist = allowlist
        self.datasource_type = self._infer_type(path, datasource_type)
        self._connection: Any | None = None

    def _infer_type(self, path: str | DatabaseConfig, hint: str | None) -> DataSourceType:
        """Infer datasource type from path or hint.

        Args:
            path: File path or config
            hint: Optional type hint

        Returns:
            Inferred DataSourceType

        Raises:
            SchemaError: If type cannot be determined
        """
        if isinstance(path, PostgresConfig):
            return DataSourceType.POSTGRES
        if isinstance(path, MySQLConfig):
            return DataSourceType.MYSQL
        if isinstance(path, MSSQLConfig):
            return DataSourceType.MSSQL

        if hint:
            try:
                return DataSourceType(hint.lower())
            except ValueError:
                raise SchemaError(f"Unknown datasource type: {hint}")

        if isinstance(path, str):
            if os.path.isdir(path):
                return DataSourceType.DIRECTORY

            # Infer from extension
            ext = os.path.splitext(path)[1].lower()
            if ext == ".parquet":
                return DataSourceType.PARQUET
            elif ext == ".csv":
                return DataSourceType.CSV
            elif ext == ".duckdb":
                return DataSourceType.DUCKDB

            raise SchemaError(f"Cannot infer type from extension: {ext}")

        raise SchemaError(f"Unsupported config type: {type(path)}")

    def _get_connection(self) -> Any:
        """Get or create DuckDB connection.

        Returns:
            DuckDB connection
        """
        if self._connection is None:
            if getattr(self, "datasource_type", None) == DataSourceType.DUCKDB and isinstance(
                self.path, str
            ):
                self._connection = duckdb.connect(self.path)
            else:
                self._connection = duckdb.connect(":memory:")
        return self._connection

    def introspect(self, name: str = "", description: str | None = None) -> DataSourceSchema:
        """Introspect datasource schema.

        Args:
            name: Optional name for datasource
            description: Optional description

        Returns:
            DataSourceSchema with tables and columns

        Raises:
            SchemaError: If introspection fails
        """
        logger.info(f"Introspecting {self.datasource_type.value} datasource")

        conn = self._get_connection()

        try:
            # Register the datasource
            tables = []

            if self.datasource_type in (
                DataSourceType.POSTGRES,
                DataSourceType.MYSQL,
                DataSourceType.MSSQL,
            ):
                uri = self.path.uri
                if self.datasource_type == DataSourceType.POSTGRES:
                    conn.execute("INSTALL postgres; LOAD postgres;")
                    conn.execute(f"ATTACH '{uri}' AS ext_db (TYPE POSTGRES);")
                elif self.datasource_type == DataSourceType.MYSQL:
                    conn.execute("INSTALL mysql; LOAD mysql;")
                    conn.execute(f"ATTACH '{uri}' AS ext_db (TYPE MYSQL);")
                elif self.datasource_type == DataSourceType.MSSQL:
                    conn.execute("INSTALL odbc; LOAD odbc;")
                    conn.execute(f"ATTACH '{uri}' AS ext_db (TYPE ODBC);")

                rs = conn.execute(
                    "SELECT table_name FROM information_schema.tables WHERE table_type='BASE TABLE' AND table_schema NOT IN ('pg_catalog', 'information_schema', 'sys', 'guest')"
                ).fetchall()
                for row in rs:
                    tables.append(row[0])

                if self.allowlist:
                    tables = [t for t in tables if t in self.allowlist]

            elif isinstance(self.path, str):
                safe_path = self.path.replace("\\", "/")
                if self.datasource_type == DataSourceType.PARQUET:
                    table_name = os.path.splitext(os.path.basename(self.path))[0]
                    conn.execute(
                        f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM '{safe_path}'"
                    )
                    tables = [table_name]
                elif self.datasource_type == DataSourceType.CSV:
                    table_name = os.path.splitext(os.path.basename(self.path))[0]
                    conn.execute(
                        f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM '{safe_path}'"
                    )
                    tables = [table_name]
                elif self.datasource_type == DataSourceType.DIRECTORY:
                    for file in os.listdir(self.path):
                        ext = os.path.splitext(file)[1].lower()
                        if ext in [".parquet", ".csv"]:
                            table_name = os.path.splitext(file)[0]
                            file_path = os.path.join(self.path, file).replace("\\", "/")
                            conn.execute(
                                f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM '{file_path}'"
                            )
                            tables.append(table_name)
                elif self.datasource_type == DataSourceType.DUCKDB:
                    # For DuckDB, get existing tables
                    result = conn.execute(
                        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
                    ).fetchall()
                    tables = [row[0] for row in result]
                else:
                    raise SchemaError(f"Unsupported datasource type: {self.datasource_type}")

            # Introspect each table
            table_infos = []
            for table_name in tables:
                table_info = self._introspect_table(conn, table_name)
                table_infos.append(table_info)

            if isinstance(self.path, str):
                datasource_name = name or os.path.splitext(os.path.basename(self.path))[0]
            else:
                datasource_name = name or self.datasource_type.value

            schema = DataSourceSchema(
                name=datasource_name,
                description=description,
                datasource_type=self.datasource_type,
                table_count=len(table_infos),
                tables=table_infos,
            )

            logger.info(f"Successfully introspected {len(table_infos)} tables")
            return schema

        except Exception as e:
            logger.error(f"Introspection failed: {e}")
            raise SchemaError(f"Failed to introspect datasource: {e}") from e

    def _introspect_table(self, conn: Any, table_name: str) -> TableInfo:
        """Introspect a single table.

        Args:
            conn: DuckDB connection
            table_name: Name of table

        Returns:
            TableInfo with columns
        """
        # Prefix external DB tables correctly if it's attached as `ext_db`
        actual_table_name = (
            f"ext_db.{table_name}"
            if self.datasource_type
            in (DataSourceType.POSTGRES, DataSourceType.MYSQL, DataSourceType.MSSQL)
            else table_name
        )

        # Get row count
        row_count_result = conn.execute(f"SELECT COUNT(*) FROM {actual_table_name}").fetchall()
        row_count = row_count_result[0][0] if row_count_result else 0

        # Get column information
        columns_result = conn.execute(f"PRAGMA table_info({actual_table_name})").fetchall()
        columns = []

        for col_info in columns_result:
            # PRAGMA table_info returns: (cid, name, type, notnull, dflt_value, pk)
            col_name = col_info[1]
            col_type = col_info[2]
            not_null = col_info[3]

            column = ColumnInfo(
                name=col_name,
                type=col_type,
                nullable=not not_null,
                description=None,
            )
            columns.append(column)

        return TableInfo(
            name=table_name,
            description=None,
            row_count=row_count,
            columns=columns,
        )

    def close(self) -> None:
        """Close database connection."""
        conn = getattr(self, "_connection", None)
        if conn is not None:
            conn.close()
            self._connection = None

    def __del__(self) -> None:
        """Ensure connection is closed."""
        self.close()
