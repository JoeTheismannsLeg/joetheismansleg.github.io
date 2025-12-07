"""Exception types for fantasy league data processing."""


class LeagueError(Exception):
    """Base exception for all league data errors."""
    pass


class APIError(LeagueError):
    """Raised when API returns an error."""
    pass


class DataValidationError(LeagueError):
    """Raised when data validation fails."""
    pass


class CacheError(LeagueError):
    """Raised when cache operations fail."""
    pass


class ConfigurationError(LeagueError):
    """Raised when configuration is invalid."""
    pass
