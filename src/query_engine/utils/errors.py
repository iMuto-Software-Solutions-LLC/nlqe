"""Custom exceptions for Query Engine."""


class QueryEngineError(Exception):
    """Base exception for Query Engine."""

    pass


class ConfigurationError(QueryEngineError):
    """Configuration is missing or invalid."""

    pass


class DataSourceError(QueryEngineError):
    """Problem with datasource."""

    pass


class FileNotFoundError(DataSourceError):
    """Datasource file not found."""

    pass


class DataFormatError(DataSourceError):
    """Invalid data format."""

    pass


class SchemaError(DataSourceError):
    """Schema-related error."""

    pass


class QueryExecutionError(QueryEngineError):
    """Problem executing query."""

    pass


class SQLSyntaxError(QueryExecutionError):
    """SQL syntax error."""

    pass


class SQLSchemaError(QueryExecutionError):
    """SQL references non-existent tables/columns."""

    pass


class SQLSafetyError(QueryExecutionError):
    """SQL contains dangerous operations."""

    pass


class QueryTimeoutError(QueryExecutionError):
    """Query execution timeout."""

    pass


class DebugFailedError(QueryExecutionError):
    """Query failed after all debug attempts."""

    pass


class APIError(QueryEngineError):
    """OpenAI API error."""

    pass


class APIAuthenticationError(APIError):
    """API authentication failed."""

    pass


class APIRateLimitError(APIError):
    """API rate limit exceeded."""

    pass


class APIUnavailableError(APIError):
    """API is unavailable."""

    pass


class APIParsingError(APIError):
    """Could not parse API response."""

    pass


class ConversationError(QueryEngineError):
    """Conversation-related error."""

    pass


class AmbiguityResolutionError(ConversationError):
    """Could not resolve ambiguous reference."""

    pass
