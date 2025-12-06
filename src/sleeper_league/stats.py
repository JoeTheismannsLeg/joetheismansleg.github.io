"""Statistics calculation utilities for Sleeper league data."""

import pandas as pd


def calculate_standings(matchups_df: pd.DataFrame) -> pd.DataFrame:
    """Calculate win-loss records and points for/against for each team."""
    if matchups_df.empty:
        return pd.DataFrame()
    
    standings = {}
    
    for _, row in matchups_df.iterrows():
        team1 = row.get('Team 1')
        team2 = row.get('Team 2')
        score1 = pd.to_numeric(row.get('Score 1'), errors='coerce')
        score2 = pd.to_numeric(row.get('Score 2'), errors='coerce')
        
        # Skip bye weeks and incomplete matchups
        if team1 in ['BYE', 'UNPLAYED/INCOMPLETE'] or team2 in ['BYE', 'UNPLAYED/INCOMPLETE']:
            continue
        if pd.isna(score1) or pd.isna(score2):
            continue
        
        # Initialize teams
        if team1 not in standings:
            standings[team1] = {'wins': 0, 'losses': 0, 'pf': 0, 'pa': 0}
        if team2 not in standings:
            standings[team2] = {'wins': 0, 'losses': 0, 'pf': 0, 'pa': 0}
        
        # Update records
        standings[team1]['pf'] += score1
        standings[team1]['pa'] += score2
        standings[team2]['pf'] += score2
        standings[team2]['pa'] += score1
        
        if score1 > score2:
            standings[team1]['wins'] += 1
            standings[team2]['losses'] += 1
        elif score2 > score1:
            standings[team2]['wins'] += 1
            standings[team1]['losses'] += 1
    
    # Convert to DataFrame
    standings_list = []
    for team, record in standings.items():
        wins = record['wins']
        losses = record['losses']
        pf = round(record['pf'], 2)
        pa = round(record['pa'], 2)
        win_pct = wins / (wins + losses) if (wins + losses) > 0 else 0
        standings_list.append({
            'Team': team,
            'W': wins,
            'L': losses,
            'W%': round(win_pct, 3),
            'PF': pf,
            'PA': pa
        })
    
    if standings_list:
        return pd.DataFrame(standings_list).sort_values('W', ascending=False).reset_index(drop=True)
    return pd.DataFrame()


def calculate_season_stats(matchups_df: pd.DataFrame) -> dict:
    """Calculate overall season statistics."""
    if matchups_df.empty:
        return {}
    
    # Filter out incomplete matchups
    valid_matchups = matchups_df[
        (matchups_df['Team 2'] != 'UNPLAYED/INCOMPLETE') &
        (matchups_df['Team 2'] != 'BYE')
    ].copy()
    
    if valid_matchups.empty:
        return {}
    
    # Convert scores to numeric
    valid_matchups['Score 1'] = pd.to_numeric(valid_matchups['Score 1'], errors='coerce')
    valid_matchups['Score 2'] = pd.to_numeric(valid_matchups['Score 2'], errors='coerce')
    valid_matchups = valid_matchups.dropna(subset=['Score 1', 'Score 2'])
    
    all_scores = pd.concat([valid_matchups['Score 1'], valid_matchups['Score 2']])
    
    if all_scores.empty:
        return {}
    
    return {
        'total_matchups': len(valid_matchups),
        'avg_points': round(all_scores.mean(), 2),
        'highest_score': round(all_scores.max(), 2),
        'lowest_score': round(all_scores.min(), 2),
        'highest_matchup': {
            'teams': None,
            'score': 0
        }
    }


def determine_matchup_winner(score1, score2) -> int:
    """
    Determine winner between two scores.
    
    Returns:
        1 if score1 wins, 2 if score2 wins, 0 if tie, None if invalid
    """
    s1 = pd.to_numeric(score1, errors='coerce')
    s2 = pd.to_numeric(score2, errors='coerce')
    
    if pd.isna(s1) or pd.isna(s2):
        return None
    
    if s1 > s2:
        return 1
    elif s2 > s1:
        return 2
    else:
        return 0  # Tie
