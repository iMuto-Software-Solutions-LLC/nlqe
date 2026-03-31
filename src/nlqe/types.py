"""Core type definitions and enums for NLQE."""

import os
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class PostgresConfig(BaseModel):
    """PostgreSQL connection configuration."""

    uri: str = Field(
        default_factory=lambda: os.getenv("NLQE_POSTGRES_URI", ""), exclude=True, repr=False
    )


class MySQLConfig(BaseModel):
    """MySQL connection configuration."""

    uri: str = Field(
        default_factory=lambda: os.getenv("NLQE_MYSQL_URI", ""), exclude=True, repr=False
    )


class MSSQLConfig(BaseModel):
    """MSSQL connection configuration."""

    uri: str = Field(
        default_factory=lambda: os.getenv("NLQE_MSSQL_URI", ""), exclude=True, repr=False
    )


DatabaseConfig = PostgresConfig | MySQLConfig | MSSQLConfig


class DataSourceType(StrEnum):
    """Supported datasource types."""

    PARQUET = "parquet"
    CSV = "csv"
    DUCKDB = "duckdb"
    DIRECTORY = "directory"
    POSTGRES = "postgres"
    MYSQL = "mysql"
    MSSQL = "mssql"


class TableInfo(BaseModel):
    """Information about a database table."""

    name: str
    description: str | None = None
    row_count: int | None = None
    columns: list["ColumnInfo"] = Field(default_factory=list)


class ColumnInfo(BaseModel):
    """Information about a database column."""

    name: str
    type: str
    nullable: bool = True
    description: str | None = None
    example_values: list[Any] | None = None


class DataSourceSchema(BaseModel):
    """Schema information for a datasource."""

    name: str
    description: str | None = None
    datasource_type: DataSourceType
    table_count: int
    tables: list[TableInfo] = Field(default_factory=list)


class ExampleQuery(BaseModel):
    """Example Q&A pattern for a datasource."""

    question: str
    sql: str
    explanation: str | None = None
    category: str | None = None


class DebugInfo(BaseModel):
    """Information about query debugging."""

    attempts: int
    errors: list[str] = Field(default_factory=list)
    modified_sqls: list[str] = Field(default_factory=list)
    first_error: str
    final_error: str | None = None


class QueryResponse(BaseModel):
    """Response from a query execution."""

    user_query: str
    generated_sql: str
    data: list[dict[str, Any]] = Field(default_factory=list)
    answer: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    execution_time_ms: float
    result_rows: int
    debug_info: DebugInfo | None = None
    error: str | None = None


class ConversationTurn(BaseModel):
    """A single turn in a multi-turn conversation."""

    turn_number: int
    user_input: str
    expanded_query: str
    generated_sql: str
    results_summary: str
    answer: str
    execution_time_ms: float
    timestamp: str | None = None


class ConversationResponse(QueryResponse):
    """Extended response for multi-turn conversations."""

    turn_number: int
    expanded_query: str
    context_used: str | None = None
    previous_results_referenced: bool = False


class SQLValidationResult(BaseModel):
    """Result of SQL validation."""

    is_valid: bool
    issues: list[str] = Field(default_factory=list)
    error_message: str | None = None
