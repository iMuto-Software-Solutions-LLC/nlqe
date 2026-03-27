import pytest

from query_engine.datasource.introspector import DataSourceIntrospector
from query_engine.types import DataSourceType
from query_engine.utils import FileNotFoundError, SchemaError


def test_introspector_file_not_found():
    with pytest.raises(FileNotFoundError):
        DataSourceIntrospector("non_existent_path.parquet")


def test_infer_type_from_hint(tmp_path):
    file_path = tmp_path / "test.xyz"
    file_path.touch()

    introspector = DataSourceIntrospector(str(file_path), datasource_type="parquet")
    assert introspector.datasource_type == DataSourceType.PARQUET


def test_infer_type_invalid_hint(tmp_path):
    file_path = tmp_path / "test.parquet"
    file_path.touch()

    with pytest.raises(SchemaError, match="Unknown datasource type"):
        DataSourceIntrospector(str(file_path), datasource_type="unknown")


def test_infer_type_unsupported_extension(tmp_path):
    file_path = tmp_path / "test.json"
    file_path.touch()

    with pytest.raises(SchemaError, match="Cannot infer type from extension"):
        DataSourceIntrospector(str(file_path))


def test_introspect_directory(tmp_path):
    import pandas as pd

    df1 = pd.DataFrame({"id": [1, 2], "val": ["A", "B"]})
    df1.to_parquet(tmp_path / "table1.parquet")

    df2 = pd.DataFrame({"x": [1.1], "y": [2.2]})
    df2.to_csv(tmp_path / "table2.csv", index=False)

    introspector = DataSourceIntrospector(str(tmp_path))
    assert introspector.datasource_type == DataSourceType.DIRECTORY

    schema = introspector.introspect()
    assert len(schema.tables) == 2

    table_names = {t.name for t in schema.tables}
    assert table_names == {"table1", "table2"}

    for t in schema.tables:
        if t.name == "table1":
            assert t.row_count == 2
            assert len(t.columns) == 2
            col_names = {c.name for c in t.columns}
            assert col_names == {"id", "val"}
        elif t.name == "table2":
            assert t.row_count == 1
            assert len(t.columns) == 2


def test_introspect_duckdb(tmp_path):
    import duckdb

    db_path = tmp_path / "test.duckdb"

    # Create a real duckdb file
    conn = duckdb.connect(str(db_path))
    conn.execute("CREATE TABLE my_table (a INTEGER, b VARCHAR)")
    conn.execute("INSERT INTO my_table VALUES (1, 'test')")
    conn.close()

    introspector = DataSourceIntrospector(str(db_path))
    assert introspector.datasource_type == DataSourceType.DUCKDB

    schema = introspector.introspect()
    assert len(schema.tables) == 1
    assert schema.tables[0].name == "my_table"
    assert schema.tables[0].row_count == 1
    assert len(schema.tables[0].columns) == 2


def test_introspect_csv(tmp_path):
    import pandas as pd

    file_path = tmp_path / "my_csv.csv"
    df = pd.DataFrame({"col1": [1, 2, 3]})
    df.to_csv(file_path, index=False)

    introspector = DataSourceIntrospector(str(file_path))
    assert introspector.datasource_type == DataSourceType.CSV

    schema = introspector.introspect(name="custom_name")
    assert schema.name == "custom_name"
    assert len(schema.tables) == 1
    assert schema.tables[0].name == "my_csv"
    assert schema.tables[0].row_count == 3
