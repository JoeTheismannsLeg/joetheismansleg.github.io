"""Configuration management for fantasy league data fetching."""

from dataclasses import dataclass
from pathlib import Path


@dataclass
class LeagueConfig:
    """Configuration for fantasy league data source."""

    league_id: str
    base_url: str = "https://api.sleeper.app/v1"
    cache_dir: Path = Path(".cache")
    request_timeout: int = 30
    max_retries: int = 3
    postseason_weeks: tuple = (14, 15, 16, 17)  # Weeks considered postseason

    def __post_init__(self):
        """Validate configuration."""
        if not self.league_id:
            raise ValueError("league_id is required")
        if self.request_timeout <= 0:
            raise ValueError("request_timeout must be positive")
        if self.max_retries < 0:
            raise ValueError("max_retries must be non-negative")
