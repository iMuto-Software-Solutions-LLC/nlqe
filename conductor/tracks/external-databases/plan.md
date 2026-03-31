# Implementation Plan: External Databases

## Phase 1: Configuration Models & Types
1.  **Update `src/nlqe/types.py`:**
    *   Add `POSTGRES`, `MYSQL`, and `MSSQL` to `DataSourceType` enum.
    *   Create new configuration classes (`PostgresConfig`, `MySQLConfig`, `MSSQLConfig`) that inherit from `BaseModel`.
    *   Use Pydantic's `Field` with `exclude=True` for passwords or connection strings to ensure they are never logged via `.model_dump()`.
    *   Define validation to require fetching connection strings from environment variables (e.g., `os.getenv("NLQE_POSTGRES_URI")`).

## Phase 2: DuckDB Executor Enhancements
1.  **Update `src/nlqe/duckdb/executor.py`:**
    *   Implement `_load_postgres()`, `_load_mysql()`, and `_load_mssql()` methods.
    *   Use `conn.execute("INSTALL postgres; LOAD postgres;")` to ensure extensions are loaded.
    *   Execute the `ATTACH '...' AS ext_db (TYPE ...)` commands.
    *   Add error handling for missing extensions or invalid connection strings.
    *   Implement `detach` cleanup logic when `close()` is called on the executor.

## Phase 3: Introspector Refactor
1.  **Update `src/nlqe/datasource/introspector.py`:**
    *   Modify `DataSourceIntrospector.__init__` to accept an `allowlist: list[str] | None = None`.
    *   Implement a new method `_introspect_duckdb_schema(conn)` that queries `information_schema.columns` from the attached database (e.g., `SELECT table_name, column_name, data_type FROM information_schema.columns WHERE table_schema='public'`).
    *   Add filtering logic: If `allowlist` is provided, only include tables in the allowlist; otherwise, introspect everything.

## Phase 4: Engine Integration & Testing
1.  **Update `src/nlqe/engine.py`:**
    *   Modify `load_datasource(...)` to accept the new Config objects (e.g., `load_datasource(config=PostgresConfig())`) and the `allowlist` parameter.
2.  **Add Unit Tests:**
    *   Mock the DuckDB `ATTACH` commands and `information_schema` queries to verify introspection logic.
    *   Test that passwords and connection strings are scrubbed from logs.
    *   Test the `allowlist` functionality (e.g., ensuring `users` is the only table returned when `allowlist=["users"]`).
3.  **Documentation:**
    *   Update `README.md` and `docs/API.md` showing how to use `PostgresConfig`, `MySQLConfig`, and `MSSQLConfig`.
    *   Add a warning explaining that users must manually install an ODBC driver for MSSQL.
