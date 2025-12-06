"""Cache utilities for Sleeper league data."""

import json
import os
import pandas as pd

CACHE_DIR = '.cache'
CACHE_FILE_TEMPLATE = os.path.join(CACHE_DIR, 'league_{league_id}_season_{season}.json')


def ensure_cache_dir():
    """Ensure cache directory exists."""
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)


def get_cache_path(league_id: str, season: str) -> str:
    """Get the cache file path for a specific league and season."""
    return CACHE_FILE_TEMPLATE.format(league_id=league_id, season=season)


def load_cached_season(league_id: str, season: str, sleeper_league_obj=None) -> dict:
    """Load cached season data if it exists and reconstruct the season data structure."""
    from .league import SleeperLeague
    
    cache_path = get_cache_path(league_id, season)
    if os.path.exists(cache_path):
        try:
            with open(cache_path, 'r') as f:
                cached_data = json.load(f)
                print(f"✓ Loaded cached data for season {season}")
                
                # If we have a sleeper_league object, use it; otherwise create a minimal one
                if sleeper_league_obj is None:
                    # Create a minimal SleeperLeague object from cached data
                    sleeper_league_obj = SleeperLeague(league_id)
                    sleeper_league_obj.user_id_to_team_name = cached_data.get('user_id_to_team_name', {})
                    sleeper_league_obj.team_name_to_user_id = cached_data.get('team_name_to_user_id', {})
                
                # Reconstruct the matchups DataFrame
                matchups_records = cached_data.get('matchups', [])
                if matchups_records and isinstance(matchups_records, list) and len(matchups_records) > 0:
                    matchups_df = pd.DataFrame(matchups_records)
                else:
                    matchups_df = pd.DataFrame()
                
                return {
                    'league': sleeper_league_obj,
                    'matchups': matchups_df,
                    'league_name': cached_data.get('league_name', 'Unknown')
                }
        except Exception as e:
            print(f"Warning: Could not load cache for season {season}: {e}")
    return None


def save_cached_season(league_id: str, season: str, data: dict):
    """Save season data to cache."""
    ensure_cache_dir()
    cache_path = get_cache_path(league_id, season)
    try:
        with open(cache_path, 'w') as f:
            json.dump(data, f)
        print(f"✓ Cached season {season} data")
    except Exception as e:
        print(f"Warning: Could not save cache for season {season}: {e}")
