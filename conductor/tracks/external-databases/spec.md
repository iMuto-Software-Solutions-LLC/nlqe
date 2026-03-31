# External Databases Support

## Overview
Enable the Natural Language Query Engine (NLQE) to query external relational databases (PostgreSQL, MySQL, and Microsoft SQL Server) using DuckDB's federated query capabilities (`ATTACH`). 

By attaching external databases, NLQE can execute natural language queries against live production data without requiring developers to export it to `.parquet` or `.csv` files first.

## Requirements

### 1. Connection Configurations
- Implement secure Pydantic configuration models (`PostgresConfig`, `MySQLConfig`, `MSSQLConfig`) that strictly load connection URIs from environment variables (e.g., `NLQE_POSTGRES_URI`).
- Prevent logging of connection strings containing passwords.

### 2. DuckDB Integration
- **PostgreSQL**: Utilize the official `postgres` extension (`ATTACH 'postgresql://...' AS pg (TYPE POSTGRES);`).
- **MySQL**: Utilize the official `mysql` extension (`ATTACH 'mysql://...' AS my (TYPE MYSQL);`).
- **MSSQL**: Utilize the `odbc` extension to attach SQL Server databases (`ATTACH 'Driver={ODBC Driver 18 for SQL Server};Server=...;' AS mssql (TYPE ODBC);`). Note: Requires users to install the appropriate OS-level ODBC driver.

### 3. Schema Introspection
- Extend `DataSourceIntrospector` to query the `information_schema` (or equivalent DuckDB metadata) of attached databases.
- By default, introspect all tables.
- Accept an optional `allowlist` of table names (e.g., `allowlist=["users", "orders"]`) to restrict the context window and speed up schema discovery.

### 4. Engine Updates
- Modify `QueryEngine.load_datasource(...)` to accept database connection configurations.
- Ensure proper cleanup and detachment of external databases when `QueryEngine` is closed.

## Out of Scope
- Direct data extraction/ETL via Python drivers (e.g., SQLAlchemy/pandas). We rely entirely on DuckDB's execution engine to push down operations to the external databases.
- Managing OS-level ODBC driver installation (this must be documented for users).
