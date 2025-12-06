"""Sleeper League - Fantasy football league data fetcher and analyzer."""

# Legacy APIs (v1)
from .league import SleeperLeague
from .stats import calculate_standings, calculate_season_stats, determine_matchup_winner
from .cache import load_cached_season, save_cached_season, ensure_cache_dir, get_cache_path
from .html import generate_matchup_html

# Modern APIs (v2)
from .config import LeagueConfig
from .exceptions import (
    SleeperLeagueError,
    APIError,
    DataValidationError,
    CacheError,
    ConfigurationError,
)
from .models import TeamRecord, SeasonStats, Matchup, LeagueInfo
from .client import SleeperLeagueClient
from .stats_v2 import calculate_standings as calculate_standings_v2
from .html_v2 import generate_html

__version__ = "2.0.0"
__all__ = [
    # Legacy v1 APIs
    'SleeperLeague',
    'calculate_standings',
    'calculate_season_stats',
    'determine_matchup_winner',
    'load_cached_season',
    'save_cached_season',
    'ensure_cache_dir',
    'get_cache_path',
    'generate_matchup_html',
    # Modern v2 APIs
    'LeagueConfig',
    'SleeperLeagueClient',
    'TeamRecord',
    'SeasonStats',
    'Matchup',
    'LeagueInfo',
    'SleeperLeagueError',
    'APIError',
    'DataValidationError',
    'CacheError',
    'ConfigurationError',
    'calculate_standings_v2',
    'generate_html',
]
