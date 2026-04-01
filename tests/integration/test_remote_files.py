"""Integration tests for remote file systems (S3/HTTP/Azure)."""

import os

import duckdb
import pytest

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


@pytest.fixture(scope="session")
def azure_config():
    """Environment variables for Azurite."""
    # Standard Azurite development connection string
    conn_str = "DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;"
    os.environ["AZURE_STORAGE_CONNECTION_STRING"] = conn_str
    return {"connection_string": conn_str}


def check_minio_available(config) -> bool:
    """Check if MinIO is running and reachable."""
    try:
        conn = duckdb.connect(":memory:")
        conn.execute("INSTALL httpfs; LOAD httpfs;")
        conn.execute(f"SET s3_access_key_id='{config['key']}'")
        conn.execute(f"SET s3_secret_access_key='{config['secret']}'")
        conn.execute(f"SET s3_endpoint='{config['endpoint']}'")
        conn.execute("SET s3_use_ssl=false")
        conn.execute("SET s3_url_style='path'")  # Required for MinIO

        # Try to list or create a test table
        conn.execute("CREATE TABLE t1 AS SELECT 1 as id")
        conn.execute("COPY t1 TO 's3://test-bucket/ping.parquet'")
        return True
    except Exception as e:
        print(f"MinIO check failed: {e}")
        return False


def check_azurite_available(config) -> bool:
    """Check if Azurite service is reachable."""
    import socket
    try:
        # Just check if port 10000 is open
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        s.connect(('127.0.0.1', 10000))
        s.close()
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

    local_parquet = "fixtures/transactions.parquet"
    if not os.path.exists(local_parquet):
        pytest.skip(f"Required test fixture {local_parquet} not found")

    conn = duckdb.connect(":memory:")
    conn.execute("INSTALL httpfs; LOAD httpfs;")
    conn.execute(f"SET s3_access_key_id='{s3_config['key']}'")
    conn.execute(f"SET s3_secret_access_key='{s3_config['secret']}'")
    conn.execute(f"SET s3_endpoint='{s3_config['endpoint']}'")
    conn.execute("SET s3_use_ssl=false")
    conn.execute("SET s3_url_style='path'")
    conn.execute(
        f"COPY (SELECT * FROM '{local_parquet}') TO 's3://test-bucket/transactions.parquet'"
    )

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


def test_azure_introspection_and_query(azure_config):
    """Test full pipeline against Azurite (Azure Blob Storage)."""
    if not check_azurite_available(azure_config):
        pytest.skip("Azurite test server is not available on localhost:10000")

    local_parquet = "fixtures/transactions.parquet"
    if not os.path.exists(local_parquet):
        pytest.skip(f"Required test fixture {local_parquet} not found")

    conn = duckdb.connect(":memory:")
    conn.execute("INSTALL azure; LOAD azure;")
    conn.execute(
        f"CREATE SECRET IF NOT EXISTS az_secret (TYPE AZURE, CONNECTION_STRING '{azure_config['connection_string']}');"
    )
    
    import time
    time.sleep(2)  # Small settle time
    
    conn.execute(
        f"COPY (SELECT * FROM '{local_parquet}') TO 'azure://test-container/transactions.parquet'"
    )

    # Now test NLQE
    engine = QueryEngine(QueryEngineConfig())
    azure_path = "azure://test-container/transactions.parquet"
    schema = engine.load_datasource(azure_path)

    assert schema.datasource_type == "parquet"
    assert len(schema.tables) == 1
    assert schema.tables[0].name == "transactions"

    # Verify we can execute a query
    response = engine.query("How many transactions are there?")
    assert response.result_rows > 0
    assert response.data is not None


def test_http_introspection_and_query():
    """Test pipeline against HTTP URL using a local background server."""
    import threading
    from http.server import HTTPServer, SimpleHTTPRequestHandler

    class QuietHandler(SimpleHTTPRequestHandler):
        def log_message(self, format, *args):
            pass

    port = 8085
    server = HTTPServer(("127.0.0.1", port), QuietHandler)
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()

    try:
        url = f"http://127.0.0.1:{port}/fixtures/transactions.parquet"

        import urllib.request

        try:
            req = urllib.request.Request(url, method="HEAD")
            urllib.request.urlopen(req, timeout=2)
        except Exception:
            pytest.skip("Local test HTTP server not reachable")

        engine = QueryEngine(QueryEngineConfig())
        schema = engine.load_datasource(url)

        assert schema.datasource_type == "parquet"
        assert len(schema.tables) == 1
        assert schema.tables[0].name == "transactions"

        response = engine.query("How many transactions are there?")
        assert response.result_rows > 0
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=1)
