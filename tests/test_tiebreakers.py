"""Test tiebreaker logic with various edge cases."""

import pytest
from collections import defaultdict


def apply_tiebreakers_correct(teams_list: list[dict], head_to_head: dict) -> list[dict]:
    """
    Apply tiebreaker rules correctly.
    
    Rules:
    1. Head-to-head: A team must SWEEP all other tied teams (be undefeated against them)
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
    
    # For 3+ teams: Check for sweeps
    tied_teams = {t['team'] for t in teams_list}
    n_teams = len(tied_teams)
    
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
    sweepers = [
        team_dict for team_dict in teams_list
        if h2h_records[team_dict['team']]['losses'] == 0
        and h2h_records[team_dict['team']]['wins'] > 0  # Must have beaten at least someone
    ]
    
    # If exactly one team swept, they win outright
    if len(sweepers) == 1:
        remaining = [t for t in teams_list if t not in sweepers]
        # Recursively apply tiebreakers to remaining teams
        return sweepers + apply_tiebreakers_correct(remaining, head_to_head)
    
    # If multiple teams swept or no one swept, fall back to PF then PA
    # Sort by PF (descending), then PA (ascending)
    return sorted(teams_list, key=lambda x: (x['pf'], -x['pa']), reverse=True)


def test_three_way_tie_clear_sweep():
    """Test 3-way tie where one team swept both others."""
    teams = [
        {'team': 'A', 'wins': 6, 'losses': 7, 'pf': 1200.0, 'pa': 1300.0},
        {'team': 'B', 'wins': 6, 'losses': 7, 'pf': 1400.0, 'pa': 1250.0},
        {'team': 'C', 'wins': 6, 'losses': 7, 'pf': 1100.0, 'pa': 1350.0},
    ]
    
    # A beat both B and C (swept)
    h2h = defaultdict(lambda: defaultdict(lambda: {'wins': 0, 'losses': 0}))
    h2h['A']['B'] = {'wins': 1, 'losses': 0}
    h2h['A']['C'] = {'wins': 1, 'losses': 0}
    h2h['B']['A'] = {'wins': 0, 'losses': 1}
    h2h['B']['C'] = {'wins': 1, 'losses': 0}
    h2h['C']['A'] = {'wins': 0, 'losses': 1}
    h2h['C']['B'] = {'wins': 0, 'losses': 1}
    
    result = apply_tiebreakers_correct(teams, dict(h2h))
    
    # Expected: A (swept), B (beat C, higher PF), C
    assert result[0]['team'] == 'A', "Team A should be first (swept)"
    assert result[1]['team'] == 'B', "Team B should be second (beat C, higher PF than C)"
    assert result[2]['team'] == 'C', "Team C should be third"


def test_three_way_tie_no_sweep():
    """Test 3-way tie where no team swept (rock-paper-scissors)."""
    teams = [
        {'team': 'A', 'wins': 6, 'losses': 7, 'pf': 1400.0, 'pa': 1300.0},
        {'team': 'B', 'wins': 6, 'losses': 7, 'pf': 1200.0, 'pa': 1250.0},
        {'team': 'C', 'wins': 6, 'losses': 7, 'pf': 1300.0, 'pa': 1350.0},
    ]
    
    # A beat B, B beat C, C beat A (circular)
    h2h = defaultdict(lambda: defaultdict(lambda: {'wins': 0, 'losses': 0}))
    h2h['A']['B'] = {'wins': 1, 'losses': 0}
    h2h['A']['C'] = {'wins': 0, 'losses': 1}
    h2h['B']['A'] = {'wins': 0, 'losses': 1}
    h2h['B']['C'] = {'wins': 1, 'losses': 0}
    h2h['C']['A'] = {'wins': 1, 'losses': 0}
    h2h['C']['B'] = {'wins': 0, 'losses': 1}
    
    result = apply_tiebreakers_correct(teams, dict(h2h))
    
    # Expected: Sorted by PF (A: 1400, C: 1300, B: 1200)
    assert result[0]['team'] == 'A', "Team A should be first (highest PF)"
    assert result[1]['team'] == 'C', "Team C should be second (middle PF)"
    assert result[2]['team'] == 'B', "Team B should be third (lowest PF)"


def test_three_way_tie_one_loss_disqualifies():
    """Test that a single loss among tied teams disqualifies from H2H win."""
    teams = [
        {'team': 'A', 'wins': 6, 'losses': 7, 'pf': 1100.0, 'pa': 1300.0},
        {'team': 'B', 'wins': 6, 'losses': 7, 'pf': 1400.0, 'pa': 1250.0},
        {'team': 'C', 'wins': 6, 'losses': 7, 'pf': 1300.0, 'pa': 1350.0},
    ]
    
    # B beat A but lost to C (1-1), A beat C
    h2h = defaultdict(lambda: defaultdict(lambda: {'wins': 0, 'losses': 0}))
    h2h['A']['B'] = {'wins': 0, 'losses': 1}
    h2h['A']['C'] = {'wins': 1, 'losses': 0}
    h2h['B']['A'] = {'wins': 1, 'losses': 0}
    h2h['B']['C'] = {'wins': 0, 'losses': 1}
    h2h['C']['A'] = {'wins': 0, 'losses': 1}
    h2h['C']['B'] = {'wins': 1, 'losses': 0}
    
    result = apply_tiebreakers_correct(teams, dict(h2h))
    
    # Expected: No sweep, sort by PF (B: 1400, C: 1300, A: 1100)
    assert result[0]['team'] == 'B', "Team B should be first (highest PF)"
    assert result[1]['team'] == 'C', "Team C should be second"
    assert result[2]['team'] == 'A', "Team A should be third"


def test_four_way_tie_one_swept():
    """Test 4-way tie where one team swept all three others."""
    teams = [
        {'team': 'A', 'wins': 7, 'losses': 6, 'pf': 1500.0, 'pa': 1400.0},
        {'team': 'B', 'wins': 7, 'losses': 6, 'pf': 1400.0, 'pa': 1350.0},
        {'team': 'C', 'wins': 7, 'losses': 6, 'pf': 1300.0, 'pa': 1300.0},
        {'team': 'D', 'wins': 7, 'losses': 6, 'pf': 1200.0, 'pa': 1250.0},
    ]
    
    # A beat all others (3-0 sweep)
    h2h = defaultdict(lambda: defaultdict(lambda: {'wins': 0, 'losses': 0}))
    h2h['A']['B'] = {'wins': 1, 'losses': 0}
    h2h['A']['C'] = {'wins': 1, 'losses': 0}
    h2h['A']['D'] = {'wins': 1, 'losses': 0}
    h2h['B']['A'] = {'wins': 0, 'losses': 1}
    h2h['C']['A'] = {'wins': 0, 'losses': 1}
    h2h['D']['A'] = {'wins': 0, 'losses': 1}
    # Others have mixed records
    h2h['B']['C'] = {'wins': 1, 'losses': 0}
    h2h['C']['B'] = {'wins': 0, 'losses': 1}
    
    result = apply_tiebreakers_correct(teams, dict(h2h))
    
    # Expected: A first (swept), then B, C, D by PF
    assert result[0]['team'] == 'A', "Team A should be first (swept all)"


def test_two_way_tie_head_to_head():
    """Test simple 2-way tie with head-to-head."""
    teams = [
        {'team': 'A', 'wins': 9, 'losses': 4, 'pf': 1500.0, 'pa': 1400.0},
        {'team': 'B', 'wins': 9, 'losses': 4, 'pf': 1600.0, 'pa': 1350.0},
    ]
    
    # A beat B
    h2h = defaultdict(lambda: defaultdict(lambda: {'wins': 0, 'losses': 0}))
    h2h['A']['B'] = {'wins': 1, 'losses': 0}
    h2h['B']['A'] = {'wins': 0, 'losses': 1}
    
    result = apply_tiebreakers_correct(teams, dict(h2h))
    
    assert result[0]['team'] == 'A', "Team A should win (beat B head-to-head)"
    assert result[1]['team'] == 'B'


def test_two_way_tie_no_head_to_head_data():
    """Test 2-way tie when teams didn't play each other."""
    teams = [
        {'team': 'A', 'wins': 8, 'losses': 5, 'pf': 1600.0, 'pa': 1400.0},
        {'team': 'B', 'wins': 8, 'losses': 5, 'pf': 1500.0, 'pa': 1350.0},
    ]
    
    h2h = defaultdict(lambda: defaultdict(lambda: {'wins': 0, 'losses': 0}))
    
    result = apply_tiebreakers_correct(teams, dict(h2h))
    
    # Should fall back to PF
    assert result[0]['team'] == 'A', "Team A should win (higher PF)"
    assert result[1]['team'] == 'B'


def test_real_2025_six_seven_tie():
    """Test the actual 2025 6-7 three-way tie."""
    teams = [
        {'team': 'Wilfork For Food', 'wins': 6, 'losses': 7, 'pf': 1223.16, 'pa': 1265.20},
        {'team': 'Los Dophins', 'wins': 6, 'losses': 7, 'pf': 1453.00, 'pa': 1497.42},
        {'team': 'patjablonski', 'wins': 6, 'losses': 7, 'pf': 1124.10, 'pa': 1284.28},
    ]
    
    # Wilfork beat Los Dophins once (week 12) and patjablonski twice (weeks 5, 10)
    # Los Dophins beat patjablonski once (week 3)
    # Total among the three: Wilfork 3-0, Los Dophins 1-1, patjablonski 0-3
    h2h = defaultdict(lambda: defaultdict(lambda: {'wins': 0, 'losses': 0}))
    h2h['Wilfork For Food']['Los Dophins'] = {'wins': 1, 'losses': 0}
    h2h['Wilfork For Food']['patjablonski'] = {'wins': 2, 'losses': 0}
    h2h['Los Dophins']['Wilfork For Food'] = {'wins': 0, 'losses': 1}
    h2h['Los Dophins']['patjablonski'] = {'wins': 1, 'losses': 0}
    h2h['patjablonski']['Wilfork For Food'] = {'wins': 0, 'losses': 2}
    h2h['patjablonski']['Los Dophins'] = {'wins': 0, 'losses': 1}
    
    result = apply_tiebreakers_correct(teams, dict(h2h))
    
    # Expected: Wilfork swept (3-0), so should be first
    # Then Los Dophins vs patjablonski: Los Dophins won H2H, so second
    assert result[0]['team'] == 'Wilfork For Food', f"Wilfork should be first (swept), got {result[0]['team']}"
    assert result[1]['team'] == 'Los Dophins', f"Los Dophins should be second, got {result[1]['team']}"
    assert result[2]['team'] == 'patjablonski', f"patjablonski should be third, got {result[2]['team']}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
