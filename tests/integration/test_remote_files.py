"""Integration tests for remote file systems (S3/HTTP)."""

import os
import pytest
import duckdb

from nlqe.config import QueryEngineConfig
from nlqe.engine import QueryEngine
from nlqe.utils import is_remote_path


@pytest.fixture(scope="session")
def s3_config():
    """Environment variables for MinIO."""
    os.environ["AWS_ACCESS_KEY_ID"] = "minio_user"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "minio_password"
    os.environ["AWS_REGION"] = "us-east-1"
    os.environ["AWS_ENDPOINT_URL_S3"] = "http://localhost:9000"
    return {
        "key": "minio_user",
        "secret": "minio_password",
        "endpoint": "localhost:9000",
    }


def check_minio_available(config) -> bool:
    """Check if MinIO is running and reachable."""
    try:
        conn = duckdb.connect(':memory:')
        conn.execute("INSTALL httpfs; LOAD httpfs;")
        conn.execute(f"SET s3_access_key_id='{config['key']}'")
        conn.execute(f"SET s3_secret_access_key='{config['secret']}'")
        conn.execute(f"SET s3_endpoint='{config['endpoint']}'")
        conn.execute("SET s3_use_ssl=false")
        # Try to list or create a test table
        conn.execute("CREATE TABLE t1 AS SELECT 1 as id")
        conn.execute("COPY t1 TO 's3://test-bucket/ping.parquet'")
        return True
    except Exception:
        return False


def test_is_remote_path():
    """Test remote path detection utility."""
    assert is_remote_path("s3://bucket/file.parquet") is True
    assert is_remote_path("https://example.com/data.csv") is True
    assert is_remote_path("http://localhost:8000/data.parquet") is True
    assert is_remote_path("azure://account/container/file.csv") is True
    assert is_remote_path("gs://bucket/file.parquet") is True
    assert is_remote_path("./local/file.parquet") is False
    assert is_remote_path("C:\\Users\\file.csv") is False
    assert is_remote_path(None) is False


def test_s3_introspection_and_query(s3_config):
    """Test full pipeline against MinIO (S3 compatible)."""
    if not check_minio_available(s3_config):
        pytest.skip("MinIO test server is not available on localhost:9000")

    # Upload sample data to MinIO via DuckDB first
    local_parquet = "fixtures/transactions.parquet"
    if not os.path.exists(local_parquet):
        pytest.skip(f"Required test fixture {local_parquet} not found")

    conn = duckdb.connect(':memory:')
    conn.execute("INSTALL httpfs; LOAD httpfs;")
    conn.execute(f"SET s3_access_key_id='{s3_config['key']}'")
    conn.execute(f"SET s3_secret_access_key='{s3_config['secret']}'")
    conn.execute(f"SET s3_endpoint='{s3_config['endpoint']}'")
    conn.execute("SET s3_use_ssl=false")
    conn.execute(f"COPY (SELECT * FROM '{local_parquet}') TO 's3://test-bucket/transactions.parquet'")

    # Now test NLQE
    engine = QueryEngine(QueryEngineConfig())
    s3_path = "s3://test-bucket/transactions.parquet"
    schema = engine.load_datasource(s3_path)

    assert schema.datasource_type == "parquet"
    assert len(schema.tables) == 1
    assert schema.tables[0].name == "transactions"
    
    # Verify we can execute a query
    response = engine.query("How many transactions are there?")
    assert response.result_rows > 0
    assert response.data is not None


def test_http_introspection_and_query():
    """Test pipeline against HTTP URL.
    
    Note: We'll use a local mock or a very stable public URL.
    For this test, we skip if no network or specific URL fails.
    """
    # Using a small, stable parquet file from DuckDB's own test data if possible
    # or just a known public one.
    url = "https://raw.githubusercontent.com/duckdb/duckdb/master/data/parquet-testing/amendments.parquet"
    
    try:
        import requests
        r = requests.head(url, timeout=5)
        if r.status_code != 200:
            pytest.skip("Public test URL not reachable")
    except Exception:
        pytest.skip("Network or requests unavailable")

    engine = QueryEngine(QueryEngineConfig())
    schema = engine.load_datasource(url)

    assert schema.datasource_type == "parquet"
    assert len(schema.tables) == 1
    assert schema.tables[0].name == "amendments"
