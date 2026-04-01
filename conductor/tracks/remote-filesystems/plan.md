# Implementation Plan: Remote File Systems

## Phase 1: Core Support in Introspector & Executor
1.  **Helper Utilities:**
    *   Create a utility function to identify remote paths (checking for prefixes like `s3://`, `http`, etc.).
2.  **Update `src/nlqe/datasource/introspector.py`:**
    *   Modify `__init__` to skip `os.path.exists()` if the path is remote.
    *   Update `introspect()` to load `httpfs` extension when needed.
3.  **Update `src/nlqe/duckdb/executor.py`:**
    *   Modify `_setup_datasource()` to handle remote URIs.
    *   Ensure `httpfs` is loaded.
    *   Optionally configure DuckDB S3/Azure settings from environment variables (e.g., `s3_access_key_id`, `s3_secret_access_key`, `s3_region`, `s3_endpoint`).

## Phase 2: Docker & Infrastructure
1.  **Update `docker-compose.yml`:**
    *   Add **MinIO** service.
    *   Add a `createbuckets` helper service to automatically create a `test-bucket` on startup.
2.  **Environment Variables:**
    *   Update `.env.example` with standard DuckDB/S3 configuration variables.

## Phase 3: Integration Testing
1.  **Create `tests/integration/test_remote_files.py`:**
    *   Implement a setup fixture that uploads `fixtures/transactions.parquet` to the local MinIO instance.
    *   Run NLQE queries against the `s3://test-bucket/transactions.parquet` path.
    *   Test HTTP access by pointing to a known stable public dataset if possible, or mocking a local HTTP server.

## Phase 4: Final Polish
1.  **Documentation:**
    *   Add "Querying Remote Files" section to `README.md`.
    *   Detail S3/Azure configuration in `docs/API.md`.
2.  **Validation:**
    *   Ensure all tests pass and `mypy`/`ruff` are satisfied.
