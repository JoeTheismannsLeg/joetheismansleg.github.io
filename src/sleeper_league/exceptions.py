"""Exception types for Sleeper League module."""


class SleeperLeagueError(Exception):
    """Base exception for all Sleeper League errors."""
    pass


class APIError(SleeperLeagueError):
    """Raised when Sleeper API returns an error."""
    pass


class DataValidationError(SleeperLeagueError):
    """Raised when data validation fails."""
    pass


class CacheError(SleeperLeagueError):
    """Raised when cache operations fail."""
    pass


class ConfigurationError(SleeperLeagueError):
    """Raised when configuration is invalid."""
    pass
