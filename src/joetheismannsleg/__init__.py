"""Fantasy League Data - Modern fantasy football league data fetcher and analyzer."""

from .config import LeagueConfig
from .exceptions import (
    LeagueError,
    APIError,
    DataValidationError,
    CacheError,
    ConfigurationError,
)
from .models import TeamRecord, SeasonStats, Matchup, LeagueInfo, LuckStats

# Data layer imports
from .data.client import LeagueClient
from .data.league import League

# Calculations layer imports
from .calculations import (
    calculate_standings,
    calculate_season_stats,
    determine_matchup_winner,
    calculate_luck_stats,
    calculate_cumulative_luck_stats,
    luck_stats_to_dataframe,
)

# UI layer imports
from .ui import generate_html

__version__ = "2.0.0"
__all__ = [
    # Core Client
    'LeagueClient',
    # Configuration
    'LeagueConfig',
    # Models
    'TeamRecord',
    'SeasonStats',
    'Matchup',
    'LeagueInfo',
    'LuckStats',
    # Exceptions
    'LeagueError',
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
    'League',
]
