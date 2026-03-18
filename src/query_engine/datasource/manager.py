"""Datasource management."""

from query_engine.datasource.introspector import DataSourceIntrospector
from query_engine.types import DataSourceSchema
from query_engine.utils import get_logger

logger = get_logger(__name__)


class DataSourceManager:
    """Manages datasource lifecycle and access."""

    def __init__(self) -> None:
        """Initialize datasource manager."""
        self._introspector: DataSourceIntrospector | None = None
        self._schema: DataSourceSchema | None = None
        self._path: str | None = None

    def load_datasource(
        self,
        path: str,
        name: str | None = None,
        description: str | None = None,
        datasource_type: str | None = None,
    ) -> DataSourceSchema:
        """Load a datasource.

        Args:
            path: Path to datasource file
            name: Optional name for datasource
            description: Optional description
            datasource_type: Optional type hint (parquet, csv, duckdb)

        Returns:
            DataSourceSchema

        Raises:
            FileNotFoundError: If file doesn't exist
            SchemaError: If format is invalid
        """
        logger.info(f"Loading datasource from {path}")

        # Close existing connection
        if self._introspector:
            self._introspector.close()

        # Create new introspector
        self._introspector = DataSourceIntrospector(path, datasource_type)
        self._path = path

        # Introspect schema
        self._schema = self._introspector.introspect(name=name or "", description=description)

        logger.info(f"Datasource loaded: {self._schema.name}")
        return self._schema

    def get_schema(self) -> DataSourceSchema | None:
        """Get current datasource schema.

        Returns:
            DataSourceSchema or None if no datasource loaded
        """
        return self._schema

    def get_path(self) -> str | None:
        """Get current datasource path.

        Returns:
            Path or None if no datasource loaded
        """
        return self._path

    def close(self) -> None:
        """Close datasource connection."""
        if self._introspector:
            self._introspector.close()
            self._introspector = None
        self._schema = None
        self._path = None

    def __del__(self) -> None:
        """Ensure datasource is closed."""
        self.close()
