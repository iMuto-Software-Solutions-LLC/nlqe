"""Integration tests for external databases (PostgreSQL, MySQL)."""

import os
import pytest
import duckdb

from nlqe.config import QueryEngineConfig
from nlqe.engine import QueryEngine
from nlqe.types import PostgresConfig, MySQLConfig


@pytest.fixture(scope="session")
def postgres_uri():
    """Default URI for the docker-compose postgres test DB."""
    return os.getenv("NLQE_POSTGRES_URI", "postgresql://test_user:test_password@localhost:5432/test_db")


@pytest.fixture(scope="session")
def mysql_uri():
    """Default URI for the docker-compose mysql test DB."""
    return os.getenv("NLQE_MYSQL_URI", "mysql://test_user:test_password@localhost:3306/test_db")


@pytest.fixture
def pg_config(postgres_uri):
    """PostgreSQL configuration mapped to environment for testing."""
    os.environ["NLQE_POSTGRES_URI"] = postgres_uri
    return PostgresConfig()


@pytest.fixture
def mysql_config(mysql_uri):
    """MySQL configuration mapped to environment for testing."""
    os.environ["NLQE_MYSQL_URI"] = mysql_uri
    return MySQLConfig()


def check_postgres_available(uri: str) -> bool:
    """Helper to check if Postgres is running and reachable by DuckDB."""
    try:
        conn = duckdb.connect(':memory:')
        conn.execute("INSTALL postgres; LOAD postgres;")
        conn.execute(f"ATTACH '{uri}' AS pg (TYPE POSTGRES);")
        return True
    except Exception:
        return False


def check_mysql_available(uri: str) -> bool:
    """Helper to check if MySQL is running and reachable by DuckDB."""
    try:
        conn = duckdb.connect(':memory:')
        conn.execute("INSTALL mysql; LOAD mysql;")
        conn.execute(f"ATTACH '{uri}' AS mysql (TYPE MYSQL);")
        return True
    except Exception:
        return False


def test_postgres_introspection_and_query(pg_config, postgres_uri):
    """Test full pipeline against live PostgreSQL database."""
    if not check_postgres_available(postgres_uri):
        pytest.skip("PostgreSQL test database is not available on localhost:5432")

    engine = QueryEngine(QueryEngineConfig())
    schema = engine.load_datasource(pg_config)

    assert schema.datasource_type == "postgres"
    
    table_names = [t.name for t in schema.tables]
    assert "users" in table_names
    assert "orders" in table_names
    assert "products" in table_names

    # Test allowlist
    schema_filtered = engine.load_datasource(pg_config, allowlist=["users"])
    assert len(schema_filtered.tables) == 1
    assert schema_filtered.tables[0].name == "users"
    assert schema_filtered.tables[0].row_count == 3


def test_mysql_introspection_and_query(mysql_config, mysql_uri):
    """Test full pipeline against live MySQL database."""
    if not check_mysql_available(mysql_uri):
        pytest.skip("MySQL test database is not available on localhost:3306")

    engine = QueryEngine(QueryEngineConfig())
    schema = engine.load_datasource(mysql_config)

    assert schema.datasource_type == "mysql"
    
    table_names = [t.name for t in schema.tables]
    assert "users" in table_names
    assert "orders" in table_names
    assert "products" in table_names

    # Test allowlist
    schema_filtered = engine.load_datasource(mysql_config, allowlist=["products"])
    assert len(schema_filtered.tables) == 1
    assert schema_filtered.tables[0].name == "products"
    assert schema_filtered.tables[0].row_count == 3
