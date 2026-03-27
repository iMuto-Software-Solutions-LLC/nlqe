import os
import pytest
from query_engine.duckdb.executor import DuckDBExecutor
from query_engine.utils import (
    QueryTimeoutError,
    SQLSafetyError,
    SQLSchemaError,
    SQLSyntaxError,
)

def test_executor_directory_setup(tmp_path):
    import pandas as pd
    
    # Create valid duckdb loadable files
    df1 = pd.DataFrame({"id": [1, 2]})
    df1.to_parquet(tmp_path / "table1.parquet")
    
    executor = DuckDBExecutor(str(tmp_path))
    # Test valid execution
    success, result = executor.execute("SELECT COUNT(*) as cnt FROM table1")
    assert success is True
    assert result[0]["cnt"] == 2
    executor.close()

def test_executor_parquet_setup(tmp_path):
    import pandas as pd
    file_path = tmp_path / "test_data.parquet"
    df = pd.DataFrame({"val": ["A", "B", "C"]})
    df.to_parquet(file_path)
    
    executor = DuckDBExecutor(str(file_path))
    success, result = executor.execute("SELECT * FROM test_data")
    assert success is True
    assert len(result) == 3
    executor.close()

def test_executor_csv_setup(tmp_path):
    import pandas as pd
    file_path = tmp_path / "test_data.csv"
    df = pd.DataFrame({"val": [1, 2]})
    df.to_csv(file_path, index=False)
    
    executor = DuckDBExecutor(str(file_path))
    success, result = executor.execute("SELECT * FROM test_data")
    assert success is True
    assert len(result) == 2
    executor.close()

def test_executor_duckdb_setup(tmp_path):
    import duckdb
    db_path = tmp_path / "test.duckdb"
    
    conn = duckdb.connect(str(db_path))
    conn.execute("CREATE TABLE test_data (a INTEGER)")
    conn.execute("INSERT INTO test_data VALUES (1), (2), (3)")
    conn.close()
    
    executor = DuckDBExecutor(str(db_path))
    success, result = executor.execute("SELECT COUNT(*) as cnt FROM test_data")
    assert success is True
    assert result[0]["cnt"] == 3
    executor.close()

def test_executor_unsupported_format(tmp_path):
    file_path = tmp_path / "test_data.json"
    file_path.touch()
    
    with pytest.raises(RuntimeError, match="Unsupported datasource format"):
        DuckDBExecutor(str(file_path))._get_connection()

def test_validate_sql_dangerous_operations(tmp_path):
    import pandas as pd
    file_path = tmp_path / "test_data.csv"
    pd.DataFrame({"a": [1]}).to_csv(file_path, index=False)
    
    executor = DuckDBExecutor(str(file_path))
    
    # Test DELETE
    validation = executor.validate_sql("DELETE FROM test_data")
    assert not validation.is_valid
    assert any("Dangerous operation" in issue for issue in validation.issues)
    
    with pytest.raises(SQLSafetyError, match="Dangerous operation"):
        executor.execute("DELETE FROM test_data")
        
    executor.close()

def test_validate_sql_multiple_statements(tmp_path):
    import pandas as pd
    file_path = tmp_path / "test_data.csv"
    pd.DataFrame({"a": [1]}).to_csv(file_path, index=False)
    
    executor = DuckDBExecutor(str(file_path))
    validation = executor.validate_sql("SELECT * FROM test_data; SELECT * FROM test_data;")
    assert not validation.is_valid
    assert any("Multiple SQL statements not allowed" in issue for issue in validation.issues)
    executor.close()

def test_validate_sql_schema_error(tmp_path):
    import pandas as pd
    file_path = tmp_path / "test_data.csv"
    pd.DataFrame({"a": [1]}).to_csv(file_path, index=False)
    
    executor = DuckDBExecutor(str(file_path))
    
    validation = executor.validate_sql("SELECT * FROM non_existent_table")
    assert not validation.is_valid
    
    with pytest.raises(SQLSchemaError):
        executor.execute("SELECT * FROM non_existent_table")
    executor.close()

def test_validate_sql_syntax_error(tmp_path):
    import pandas as pd
    file_path = tmp_path / "test_data.csv"
    pd.DataFrame({"a": [1]}).to_csv(file_path, index=False)
    
    executor = DuckDBExecutor(str(file_path))
    
    validation = executor.validate_sql("SELECT * FROM")
    assert not validation.is_valid
    
    with pytest.raises(SQLSyntaxError):
        executor.execute("SELECT * FROM")
    executor.close()
