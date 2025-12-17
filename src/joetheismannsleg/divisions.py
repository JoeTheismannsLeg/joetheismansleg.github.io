"""Division and playoff configuration."""

# Division assignments for 2025 season
# Usernames (display_name from Sleeper API)
BOATS_USERNAMES_2025 = ["CSP3", "Ramzishu", "Favre_From_Over", "IKA", "LosDophs"]
HOES_USERNAMES_2025 = ["tombradysarm", "HideYourBeagles", "badera", "nephophobiac", "patjablonski"]

# Regular season weeks (for playoff seeding calculation)
REGULAR_SEASON_WEEKS = list(range(1, 14))  # Weeks 1-13

# Playoff weeks
PLAYOFF_WEEKS = list(range(14, 18))  # Weeks 14-17


def get_divisions_for_year(year: int, username_to_team: dict) -> tuple[list[str], list[str]]:
    """
    Get division assignments for a given year, mapped to team names.
    
    Args:
        year: Season year
        username_to_team: Mapping from username to team name
        
    Returns:
        Tuple of (boats_teams, hoes_teams) with team names
    """
    if year == 2025:
        boats_teams = [username_to_team.get(u, u) for u in BOATS_USERNAMES_2025]
        hoes_teams = [username_to_team.get(u, u) for u in HOES_USERNAMES_2025]
        return boats_teams, hoes_teams
    
    # For other years, divisions not yet configured
    # Could add historical division assignments here
    return [], []
