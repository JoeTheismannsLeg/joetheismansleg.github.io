"""Sleeper League - Modern fantasy football league data fetcher and analyzer."""

from .config import LeagueConfig
from .exceptions import (
    SleeperLeagueError,
    APIError,
    DataValidationError,
    CacheError,
    ConfigurationError,
)
from .models import TeamRecord, SeasonStats, Matchup, LeagueInfo, LuckStats
from .client import SleeperLeagueClient
from .stats import (
    calculate_standings,
    calculate_season_stats,
    determine_matchup_winner,
    calculate_luck_stats,
    calculate_cumulative_luck_stats,
    luck_stats_to_dataframe,
)
from .html import generate_html

__version__ = "2.0.0"
__all__ = [
    # Core Client
    'SleeperLeagueClient',
    # Configuration
    'LeagueConfig',
    # Models
    'TeamRecord',
    'SeasonStats',
    'Matchup',
    'LeagueInfo',
    'LuckStats',
    # Exceptions
    'SleeperLeagueError',
    'APIError',
    'DataValidationError',
    'CacheError',
    'ConfigurationError',
    # Functions
    'calculate_standings',
    'calculate_season_stats',
    'determine_matchup_winner',
    'calculate_luck_stats',
    'calculate_cumulative_luck_stats',
    'luck_stats_to_dataframe',
    'generate_html',
]
