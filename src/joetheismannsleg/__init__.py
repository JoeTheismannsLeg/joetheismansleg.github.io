"""Fantasy League Data - Modern fantasy football league data fetcher and analyzer."""

# Calculations layer imports
from .calculations import (
    calculate_cumulative_luck_stats,
    calculate_luck_stats,
    calculate_season_stats,
    calculate_standings,
    determine_matchup_winner,
    luck_stats_to_dataframe,
)
from .config import LeagueConfig

# Data layer imports
from .data.client import LeagueClient
from .data.league import League
from .exceptions import (
    APIError,
    CacheError,
    ConfigurationError,
    DataValidationError,
    LeagueError,
)
from .models import LeagueInfo, LuckStats, Matchup, SeasonStats, TeamRecord

# UI layer imports
from .ui import generate_html

__version__ = "2.0.0"
__all__ = [
    # Core Client
    "LeagueClient",
    # Configuration
    "LeagueConfig",
    # Models
    "TeamRecord",
    "SeasonStats",
    "Matchup",
    "LeagueInfo",
    "LuckStats",
    # Exceptions
    "LeagueError",
    "APIError",
    "DataValidationError",
    "CacheError",
    "ConfigurationError",
    # Functions
    "calculate_standings",
    "calculate_season_stats",
    "determine_matchup_winner",
    "calculate_luck_stats",
    "calculate_cumulative_luck_stats",
    "luck_stats_to_dataframe",
    "generate_html",
    "League",
]
