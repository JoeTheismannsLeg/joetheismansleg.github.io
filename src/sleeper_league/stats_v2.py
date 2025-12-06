"""Enhanced statistics calculation module."""

from typing import List, Dict
import pandas as pd

from .models import Matchup, TeamRecord, SeasonStats


def calculate_standings(matchups: List[Matchup]) -> List[TeamRecord]:
    """
    Calculate standings from matchups.
    
    Args:
        matchups: List of Matchup objects
        
    Returns:
        List of TeamRecord objects sorted by wins
    """
    standings: Dict[str, TeamRecord] = {}
    
    for matchup in matchups:
        # Skip bye weeks and incomplete matchups
        if matchup.is_bye() or matchup.is_incomplete():
            continue
        
        # Initialize teams if needed
        if matchup.team_1 not in standings:
            standings[matchup.team_1] = TeamRecord(team=matchup.team_1)
        if matchup.team_2 not in standings:
            standings[matchup.team_2] = TeamRecord(team=matchup.team_2)
        
        # Update points
        standings[matchup.team_1].points_for += matchup.score_1
        standings[matchup.team_1].points_against += matchup.score_2
        standings[matchup.team_2].points_for += matchup.score_2
        standings[matchup.team_2].points_against += matchup.score_1
        
        # Update wins/losses
        winner = matchup.winner()
        if winner == 1:
            standings[matchup.team_1].wins += 1
            standings[matchup.team_2].losses += 1
        elif winner == 2:
            standings[matchup.team_2].wins += 1
            standings[matchup.team_1].losses += 1
    
    # Sort by wins descending
    return sorted(standings.values(), key=lambda t: t.wins, reverse=True)


def calculate_season_stats(matchups: List[Matchup]) -> SeasonStats:
    """
    Calculate season-wide statistics.
    
    Args:
        matchups: List of Matchup objects
        
    Returns:
        SeasonStats object with aggregate data
    """
    # Filter valid matchups
    valid = [m for m in matchups if not m.is_bye() and not m.is_incomplete()]
    
    if not valid:
        return SeasonStats()
    
    all_scores = [m.score_1 for m in valid] + [m.score_2 for m in valid]
    
    return SeasonStats(
        total_matchups=len(valid),
        avg_points=sum(all_scores) / len(all_scores) if all_scores else 0.0,
        highest_score=max(all_scores) if all_scores else 0.0,
        lowest_score=min(all_scores) if all_scores else 0.0,
    )


def standings_to_dataframe(standings: List[TeamRecord]) -> pd.DataFrame:
    """
    Convert standings to DataFrame.
    
    Args:
        standings: List of TeamRecord objects
        
    Returns:
        DataFrame with standings data
    """
    if not standings:
        return pd.DataFrame()
    
    return pd.DataFrame([s.to_dict() for s in standings])
