"""Utilities for NLQE."""

from nlqe.utils.errors import (
    AmbiguityResolutionError,
    APIAuthenticationError,
    APIError,
    APIParsingError,
    APIRateLimitError,
    APIUnavailableError,
    ConfigurationError,
    ConversationError,
    DataFormatError,
    DataSourceError,
    DebugFailedError,
    FileNotFoundError,
    QueryEngineError,
    QueryExecutionError,
    QueryTimeoutError,
    SchemaError,
    SQLSafetyError,
    SQLSchemaError,
    SQLSyntaxError,
)
from nlqe.utils.logging import get_logger, setup_logging

def is_remote_path(path: object) -> bool:
    """Check if a path is a remote URI.

    Args:
        path: Path to check

    Returns:
        True if path starts with a remote scheme (s3, http, etc.)
    """
    if not isinstance(path, str):
        return False
    
    remote_schemes = ("s3://", "https://", "http://", "azure://", "gs://", "wasb://")
    return path.lower().startswith(remote_schemes)


__all__ = [
    "is_remote_path",
    "APIAuthenticationError",
    "APIError",
    "APIParsingError",
    "APIRateLimitError",
    "APIUnavailableError",
    "AmbiguityResolutionError",
    "ConfigurationError",
    "ConversationError",
    "DataFormatError",
    "DataSourceError",
    "DebugFailedError",
    "FileNotFoundError",
    "QueryEngineError",
    "QueryExecutionError",
    "QueryTimeoutError",
    "SQLSafetyError",
    "SQLSchemaError",
    "SQLSyntaxError",
    "SchemaError",
    "get_logger",
    "setup_logging",
]
