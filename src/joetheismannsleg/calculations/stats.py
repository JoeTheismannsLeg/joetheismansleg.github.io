"""Statistics calculation module."""

from typing import Dict, List, Tuple

import pandas as pd

from ..models import LuckStats, Matchup, SeasonStats, TeamRecord


def calculate_standings(matchups: List[Matchup]) -> List[TeamRecord]:
    """
    Calculate standings from matchups.

    Args:
        matchups: List of Matchup objects

    Returns:
        List of TeamRecord objects sorted by wins
    """
    standings: dict = {}

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
    Convert standings to DataFrame for compatibility.

    Args:
        standings: List of TeamRecord objects

    Returns:
        DataFrame with standings data
    """
    if not standings:
        return pd.DataFrame()

    return pd.DataFrame([s.to_dict() for s in standings])


def determine_matchup_winner(matchup: Matchup) -> int:
    """
    Determine winner of a matchup.

    Args:
        matchup: Matchup object

    Returns:
        1 if team 1 wins, 2 if team 2 wins, 0 if tie/incomplete
    """
    return matchup.winner()


def calculate_luck_stats(matchups: List[Matchup]) -> List[LuckStats]:
    """
    Calculate "Behind the Cue Ball" luck statistics.

    For each team, each week calculates:
    - Actual record from real matchups
    - True record if they played all other teams that week
    - Luck factor (actual win % - true win %)

    Args:
        matchups: List of Matchup objects

    Returns:
        List of LuckStats objects
    """
    # Filter valid matchups only
    valid_matchups = [m for m in matchups if not m.is_bye() and not m.is_incomplete()]

    # Group matchups by week
    matchups_by_week: Dict[int, List[Matchup]] = {}
    for m in valid_matchups:
        if m.week not in matchups_by_week:
            matchups_by_week[m.week] = []
        matchups_by_week[m.week].append(m)

    # Get all teams
    all_teams = set()
    for m in valid_matchups:
        all_teams.add(m.team_1)
        all_teams.add(m.team_2)

    luck_stats_list = []

    # Calculate for each week
    for week in sorted(matchups_by_week.keys()):
        week_matchups = matchups_by_week[week]

        # Get team scores for this week
        team_scores: Dict[str, float] = {}
        for m in week_matchups:
            team_scores[m.team_1] = m.score_1
            team_scores[m.team_2] = m.score_2

        # Calculate stats for each team
        for team in all_teams:
            if team not in team_scores:
                continue

            team_score = team_scores[team]

            # Calculate actual record (from real matchups)
            actual_wins = 0
            actual_losses = 0

            for m in week_matchups:
                if m.team_1 == team:
                    if m.score_1 > m.score_2:
                        actual_wins += 1
                    else:
                        actual_losses += 1
                elif m.team_2 == team:
                    if m.score_2 > m.score_1:
                        actual_wins += 1
                    else:
                        actual_losses += 1

            # Calculate true record (if played all other teams)
            true_wins = 0
            true_losses = 0

            for other_team in all_teams:
                if other_team == team:
                    continue

                if other_team in team_scores:
                    if team_score > team_scores[other_team]:
                        true_wins += 1
                    else:
                        true_losses += 1

            # Create LuckStats object
            luck_stat = LuckStats(
                team=team,
                week=week,
                actual_wins=actual_wins,
                actual_losses=actual_losses,
                true_wins=true_wins,
                true_losses=true_losses,
            )

            luck_stats_list.append(luck_stat)

    return luck_stats_list


def calculate_cumulative_luck_stats(matchups: List[Matchup]) -> List[Dict]:
    """
    Calculate cumulative "Behind the Cue Ball" stats season-to-date.

    For each team, for each week, calculates cumulative stats from week 1 to that week.
    Also includes week-only stats for comparison.

    Args:
        matchups: List of Matchup objects

    Returns:
        List of dictionaries with cumulative and weekly stats
    """
    # Get weekly luck stats first
    weekly_stats = calculate_luck_stats(matchups)

    # Group by team and week
    stats_by_team_week: Dict[Tuple[str, int], LuckStats] = {}
    for stat in weekly_stats:
        stats_by_team_week[(stat.team, stat.week)] = stat

    # Get all teams and weeks
    all_teams = set()
    all_weeks = set()
    for stat in weekly_stats:
        all_teams.add(stat.team)
        all_weeks.add(stat.week)

    result = []

    # Calculate cumulative stats for each team and week
    for team in sorted(all_teams):
        cumulative_actual_wins = 0
        cumulative_actual_losses = 0
        cumulative_true_wins = 0
        cumulative_true_losses = 0

        prev_luck = 0.0

        for week in sorted(all_weeks):
            key = (team, week)

            if key not in stats_by_team_week:
                continue

            weekly_stat = stats_by_team_week[key]

            # Add to cumulative
            cumulative_actual_wins += weekly_stat.actual_wins
            cumulative_actual_losses += weekly_stat.actual_losses
            cumulative_true_wins += weekly_stat.true_wins
            cumulative_true_losses += weekly_stat.true_losses

            # Calculate percentages
            cum_total = cumulative_actual_wins + cumulative_actual_losses
            cum_win_pct = (cumulative_actual_wins / cum_total) if cum_total > 0 else 0.0

            cum_true_total = cumulative_true_wins + cumulative_true_losses
            cum_true_pct = (cumulative_true_wins / cum_true_total) if cum_true_total > 0 else 0.0

            cum_luck = cum_win_pct - cum_true_pct
            delta_luck = cum_luck - prev_luck
            delta_true = cum_true_pct - (
                weekly_stat.true_percentage if week > min(all_weeks) else 0.0
            )

            result.append(
                {
                    "Team": team,
                    "Week": week,
                    "Win %": f"{cum_win_pct * 100:.1f}%",
                    "True %": f"{cum_true_pct * 100:.1f}%",
                    "Delta True": f"{delta_true * 100:.1f}%",
                    "Luck": f"{cum_luck * 100:.1f}%",
                    "Delta Luck": f"{delta_luck * 100:.1f}%",
                    "Trend": "↑" if delta_luck > 0.01 else "↓" if delta_luck < -0.01 else "→",
                    "Weekly Win %": f"{weekly_stat.win_percentage * 100:.1f}%",
                    "Weekly True %": f"{weekly_stat.true_percentage * 100:.1f}%",
                    "Weekly Luck": f"{weekly_stat.luck * 100:.1f}%",
                }
            )

            prev_luck = cum_luck

    return result


def luck_stats_to_dataframe(luck_stats: List[Dict]) -> pd.DataFrame:
    """
    Convert luck stats list to DataFrame.

    Args:
        luck_stats: List of luck stat dictionaries from calculate_cumulative_luck_stats

    Returns:
        DataFrame with luck statistics
    """
    if not luck_stats:
        return pd.DataFrame()

    return pd.DataFrame(luck_stats)


def calculate_standings_with_h2h(matchups: List[Matchup]) -> Tuple[List[dict], dict]:
    """
    Calculate standings with head-to-head tracking.
    
    Args:
        matchups: List of Matchup objects
        
    Returns:
        Tuple of (standings list, head_to_head dict)
        standings: List of dicts with team, wins, losses, pf, pa
        head_to_head: Dict[team][opponent] -> {'wins': int, 'losses': int}
    """
    from collections import defaultdict
    
    standings = defaultdict(lambda: {'wins': 0, 'losses': 0, 'pf': 0.0, 'pa': 0.0})
    head_to_head = defaultdict(lambda: defaultdict(lambda: {'wins': 0, 'losses': 0}))
    
    for matchup in matchups:
        if matchup.is_bye() or matchup.is_incomplete():
            continue
        
        team1 = matchup.team_1
        team2 = matchup.team_2
        score1 = matchup.score_1
        score2 = matchup.score_2
        
        # Update points
        standings[team1]['pf'] += score1
        standings[team1]['pa'] += score2
        standings[team2]['pf'] += score2
        standings[team2]['pa'] += score1
        
        # Update wins/losses and head-to-head
        if score1 > score2:
            standings[team1]['wins'] += 1
            standings[team2]['losses'] += 1
            head_to_head[team1][team2]['wins'] += 1
            head_to_head[team2][team1]['losses'] += 1
        elif score2 > score1:
            standings[team2]['wins'] += 1
            standings[team1]['losses'] += 1
            head_to_head[team2][team1]['wins'] += 1
            head_to_head[team1][team2]['losses'] += 1
    
    # Convert to list format
    standings_list = [
        {'team': team, **stats}
        for team, stats in standings.items()
    ]
    
    return standings_list, dict(head_to_head)


def apply_tiebreakers(teams_list: List[dict], head_to_head: dict) -> List[dict]:
    """
    Apply tiebreaker rules to teams with the same record.
    
    Tiebreaker order:
    1. Head-to-head: A team must SWEEP (be undefeated against) all other tied teams
       to win via head-to-head. If no team swept or multiple teams swept, go to step 2.
    2. Points For: Higher is better
    3. Points Against: Lower is better
    
    Args:
        teams_list: List of team dicts with team, wins, losses, pf, pa
        head_to_head: Head-to-head records dict
        
    Returns:
        Sorted list of teams after applying tiebreakers
    """
    if len(teams_list) <= 1:
        return teams_list
    
    # Check if all teams have the same record
    same_record = all(t['wins'] == teams_list[0]['wins'] for t in teams_list)
    if not same_record:
        return teams_list
    
    # For 2 teams, simple head-to-head
    if len(teams_list) == 2:
        t1, t2 = teams_list[0], teams_list[1]
        h2h_wins = head_to_head.get(t1['team'], {}).get(t2['team'], {}).get('wins', 0)
        if h2h_wins > 0:
            return [t1, t2]
        elif h2h_wins == 0 and head_to_head.get(t2['team'], {}).get(t1['team'], {}).get('wins', 0) > 0:
            return [t2, t1]
        # Tie in head-to-head, go to PF
        if t1['pf'] != t2['pf']:
            return sorted(teams_list, key=lambda x: x['pf'], reverse=True)
        # Tie in PF, go to PA
        return sorted(teams_list, key=lambda x: x['pa'])
    
    # For 3+ teams: Check for sweeps (undefeated against all other tied teams)
    tied_teams = {t['team'] for t in teams_list}
    
    # Calculate H2H records among tied teams
    h2h_records = {}
    for team_dict in teams_list:
        team = team_dict['team']
        h2h_wins = sum(
            head_to_head.get(team, {}).get(opponent, {}).get('wins', 0)
            for opponent in tied_teams if opponent != team
        )
        h2h_losses = sum(
            head_to_head.get(team, {}).get(opponent, {}).get('losses', 0)
            for opponent in tied_teams if opponent != team
        )
        h2h_records[team] = {'wins': h2h_wins, 'losses': h2h_losses}
    
    # Find teams that swept (undefeated against all other tied teams)
    # A sweep means losses == 0 and wins > 0 (beat at least one tied team)
    sweepers = [
        team_dict for team_dict in teams_list
        if h2h_records[team_dict['team']]['losses'] == 0
        and h2h_records[team_dict['team']]['wins'] > 0
    ]
    
    # If exactly one team swept, they win outright
    if len(sweepers) == 1:
        remaining = [t for t in teams_list if t not in sweepers]
        # Recursively apply tiebreakers to remaining teams
        return sweepers + apply_tiebreakers(remaining, head_to_head)
    
    # If multiple teams swept or no one swept, fall back to PF then PA
    # Sort by PF (descending), then PA (ascending)
    return sorted(teams_list, key=lambda x: (x['pf'], -x['pa']), reverse=True)


def sort_teams_with_tiebreakers(teams: List[dict], head_to_head: dict) -> List[dict]:
    """
    Group teams by record and apply tiebreakers within each group.
    
    Args:
        teams: List of team dicts
        head_to_head: Head-to-head records
        
    Returns:
        Sorted list of teams
    """
    from collections import defaultdict
    
    by_record = defaultdict(list)
    for team in teams:
        by_record[team['wins']].append(team)
    
    sorted_teams = []
    for wins in sorted(by_record.keys(), reverse=True):
        tied_teams = by_record[wins]
        sorted_teams.extend(apply_tiebreakers(tied_teams, head_to_head))
    
    return sorted_teams


def calculate_playoff_seeding(
    matchups: List[Matchup],
    boats_teams: List[str],
    hoes_teams: List[str]
) -> Tuple[List[dict], List[dict]]:
    """
    Calculate playoff seeding with division winners and wildcards.
    
    Args:
        matchups: List of regular season matchups (weeks 1-13)
        boats_teams: List of team names in Boats division
        hoes_teams: List of team names in Hoes division
        
    Returns:
        Tuple of (playoff_seeds, consolation_seeds)
        Each is a list of dicts with team, wins, losses, pf, pa, division, seed_type
    """
    standings_list, head_to_head = calculate_standings_with_h2h(matchups)
    
    # Separate by division
    boats_standings = [s for s in standings_list if s['team'] in boats_teams]
    hoes_standings = [s for s in standings_list if s['team'] in hoes_teams]
    
    # Sort within divisions with tiebreakers
    boats_standings = sort_teams_with_tiebreakers(boats_standings, head_to_head)
    hoes_standings = sort_teams_with_tiebreakers(hoes_standings, head_to_head)
    
    # Division winners get top 2 seeds
    division_winners = [boats_standings[0], hoes_standings[0]]
    division_winners = apply_tiebreakers(division_winners, head_to_head)
    
    # Remaining teams compete for wildcards and consolation
    remaining_teams = boats_standings[1:] + hoes_standings[1:]
    remaining_teams = sort_teams_with_tiebreakers(remaining_teams, head_to_head)
    
    # Build seeded results
    playoff_seeds = []
    consolation_seeds = []
    
    # Seeds 1-2: Division winners
    for i, team in enumerate(division_winners, 1):
        team_copy = team.copy()
        team_copy['seed'] = i
        team_copy['division'] = 'Boats' if team['team'] in boats_teams else 'Hoes'
        team_copy['seed_type'] = 'Division Winner'
        playoff_seeds.append(team_copy)
    
    # Seeds 3-4: Wildcards
    for i, team in enumerate(remaining_teams[:2], 3):
        team_copy = team.copy()
        team_copy['seed'] = i
        team_copy['division'] = 'Boats' if team['team'] in boats_teams else 'Hoes'
        team_copy['seed_type'] = 'Wildcard'
        playoff_seeds.append(team_copy)
    
    # Seeds 5-10: Consolation
    for i, team in enumerate(remaining_teams[2:], 5):
        team_copy = team.copy()
        team_copy['seed'] = i
        team_copy['division'] = 'Boats' if team['team'] in boats_teams else 'Hoes'
        team_copy['seed_type'] = 'Consolation'
        consolation_seeds.append(team_copy)
    
    return playoff_seeds, consolation_seeds
