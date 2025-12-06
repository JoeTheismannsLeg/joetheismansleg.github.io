import requests
import pandas as pd
import datetime
import json
import re
import os

# Cache configuration
CACHE_DIR = '.cache'
CACHE_FILE_TEMPLATE = os.path.join(CACHE_DIR, 'league_{league_id}_season_{season}.json')

def ensure_cache_dir():
    """Ensure cache directory exists."""
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)

def get_cache_path(league_id: str, season: str) -> str:
    """Get the cache file path for a specific league and season."""
    return CACHE_FILE_TEMPLATE.format(league_id=league_id, season=season)

def load_cached_season(league_id: str, season: str, sleeper_league_obj: 'SleeperLeague' = None) -> dict:
    """Load cached season data if it exists and reconstruct the season data structure."""
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

def determine_matchup_winner(score1, score2):
    """Determine winner between two scores."""
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

class SleeperLeague:
    """
    A class to interact with the Sleeper API for a specific fantasy football league.
    Encapsulates methods for fetching league details, user data, roster data,
    and matchup information.
    """
    def __init__(self, league_id: str, base_url: str = 'https://api.sleeper.app/v1'):
        self.league_id = league_id
        self.base_url = base_url
        self.league_data = None
        self.users_data = None
        self.user_id_to_name = {}
        self.user_id_to_team_name = {}
        self.team_name_to_user_id = {}
        self.roster_id_to_user_id = {}
        self.roster_id_to_team_name = {}
        print(f"Initializing SleeperLeague for league ID: {self.league_id}")
        self._fetch_base_data()

    def _fetch_base_data(self):
        """
        Fetches basic league information, user data, and roster data
        and stores them as instance attributes.
        """
        print(f"Fetching base data for league ID: {self.league_id}")

        # 1. Fetch league details
        league_endpoint = f"{self.base_url}/league/{self.league_id}"
        try:
            response = requests.get(league_endpoint)
            response.raise_for_status()
            self.league_data = response.json()
            print("Successfully fetched league data.")
        except requests.exceptions.RequestException as e:
            print(f"Error fetching league data: {e}")
            self.league_data = None
            return # Exit if league data cannot be fetched

        # 2. Fetch user data
        users_endpoint = f"{self.base_url}/league/{self.league_id}/users"
        try:
            user_response = requests.get(users_endpoint)
            user_response.raise_for_status()
            self.users_data = user_response.json()
            self.user_id_to_name = {user['user_id']: user['display_name'] for user in self.users_data}
            # Also store team names from user metadata
            self.user_id_to_team_name = {}
            for user in self.users_data:
                metadata = user.get('metadata', {})
                team_name = metadata.get('team_name') if metadata else None
                if team_name:
                    self.user_id_to_team_name[user['user_id']] = team_name
            print(f"Successfully fetched user data for {len(self.user_id_to_name)} users.")
        except requests.exceptions.RequestException as e:
            print(f"Error fetching user data: {e}")
            self.users_data = None
            self.user_id_to_name = {}
            self.user_id_to_team_name = {}

        # 3. Fetch roster data
        rosters_endpoint = f"{self.base_url}/league/{self.league_id}/rosters"
        try:
            rosters_response = requests.get(rosters_endpoint)
            rosters_response.raise_for_status()
            rosters_data = rosters_response.json()
            self.roster_id_to_user_id = {}
            self.roster_id_to_team_name = {}
            self.team_name_to_user_id = {}
            for roster_entry in rosters_data:
                if roster_entry.get('owner_id'):
                    user_id = roster_entry['owner_id']
                    self.roster_id_to_user_id[roster_entry['roster_id']] = user_id
                    # Get team name from user metadata, fallback to display name
                    team_name = self.user_id_to_team_name.get(user_id)
                    if not team_name:
                        team_name = self.user_id_to_name.get(user_id, f"Unknown Team (Roster {roster_entry['roster_id']})")
                    self.roster_id_to_team_name[roster_entry['roster_id']] = team_name
                    # Map team name to user ID for easy lookup
                    self.team_name_to_user_id[team_name] = user_id
                else:
                    print(f"Roster ID {roster_entry['roster_id']} has no owner. Skipping.")
            print(f"Successfully fetched roster data for {len(self.roster_id_to_user_id)} rosters.")
        except requests.exceptions.RequestException as e:
            print(f"Error fetching roster data: {e}")
            self.roster_id_to_user_id = {}
            self.roster_id_to_team_name = {}

        if self.league_data and self.user_id_to_name and self.roster_id_to_user_id:
            print("Base data loaded successfully.")
        else:
            print("Failed to load all base data.")

    def _get_team_name(self, roster_id: int) -> str:
        """Helper to get team name from roster_id."""
        return self.roster_id_to_team_name.get(roster_id, f"Unknown Team (Roster {roster_id})")

    def fetch_weekly_matchups(self, week_number: int) -> pd.DataFrame:
        """
        Fetches and processes matchup data for a given week.

        Args:
            week_number (int): The week number to fetch matchups for.

        Returns:
            pd.DataFrame: A DataFrame containing formatted matchups for that week.
        """
        if not self.league_data or not self.user_id_to_name or not self.roster_id_to_user_id:
            print("Base league data is not loaded. Cannot fetch matchups.")
            return pd.DataFrame()

        matchups_endpoint = f"{self.base_url}/league/{self.league_id}/matchups/{week_number}"
        print(f"Fetching matchup data for week {week_number} from: {matchups_endpoint}")

        try:
            response = requests.get(matchups_endpoint)
            response.raise_for_status()
            matchup_data = response.json()
            print(f"Successfully fetched {len(matchup_data)} entries for week {week_number}.")
        except requests.exceptions.RequestException as e:
            print(f"Error fetching matchup data for week {week_number}: {e}")
            return pd.DataFrame() # Return empty DataFrame on error

        matchup_details = []
        matchups_grouped = {}
        for match in matchup_data:
            matchup_id = match['matchup_id']
            if matchup_id not in matchups_grouped:
                matchups_grouped[matchup_id] = []
            matchups_grouped[matchup_id].append(match)

        for matchup_id, teams in matchups_grouped.items():
            if len(teams) == 2: # Normal matchup
                team1 = teams[0]
                team2 = teams[1]

                team1_name = self._get_team_name(team1['roster_id'])
                team2_name = self._get_team_name(team2['roster_id'])

                team1_score = team1['points']
                team2_score = team2['points']

                matchup_details.append({
                    'Matchup ID': matchup_id,
                    'Team 1': team1_name,
                    'Score 1': team1_score,
                    'Team 2': team2_name,
                    'Score 2': team2_score
                })
            elif len(teams) == 1: # Bye week
                team1 = teams[0]
                team1_name = self._get_team_name(team1['roster_id'])
                team1_score = team1['points']
                matchup_details.append({
                    'Matchup ID': matchup_id,
                    'Team 1': team1_name,
                    'Score 1': team1_score,
                    'Team 2': 'BYE',
                    'Score 2': 'N/A'
                })
            else: # Handle incomplete/unplayed matchups (e.g., when matchup_id is None for all teams)
                # For each team in this group, create an entry indicating it's unplayed/incomplete
                for team in teams:
                    team_name = self._get_team_name(team['roster_id'])
                    team_score = team['points'] # Still show the score, it might be 0
                    matchup_details.append({
                        'Matchup ID': matchup_id, # This will be None for unplayed weeks
                        'Team 1': team_name,
                        'Score 1': team_score,
                        'Team 2': 'UNPLAYED/INCOMPLETE',
                        'Score 2': 'N/A'
                    })

        return pd.DataFrame(matchup_details)

    def fetch_all_matchups(self) -> pd.DataFrame:
        """
        Fetches matchup data for all weeks in the league (up to 17).

        Returns:
            pd.DataFrame: A single DataFrame containing all matchups for all weeks.
        """
        if not self.league_data:
            print("League data not loaded. Cannot fetch matchups.")
            return pd.DataFrame()

        # Always iterate through 17 weeks as requested
        num_total_weeks = 17

        all_matchups_dfs = []
        for week in range(1, num_total_weeks + 1):
            weekly_df = self.fetch_weekly_matchups(week)
            if not weekly_df.empty:
                weekly_df['Week'] = week # Add a 'Week' column
                all_matchups_dfs.append(weekly_df)

        if all_matchups_dfs:
            return pd.concat(all_matchups_dfs, ignore_index=True)
        else:
            return pd.DataFrame()

    def fetch_current_week_matchups(self):
        """
        Fetch matchup data only for the current active week.
        For in-season, uses the league status. For post-season, fetches all weeks.

        Returns:
            pd.DataFrame: Matchups for the current week, or all weeks if post-season.
        """
        if not self.league_data:
            print("League data not loaded. Cannot fetch current week.")
            return pd.DataFrame()

        # Check if league is in post-season or off-season
        season_status = self.league_data.get('status', 'regular')
        
        if season_status == 'post_season' or season_status == 'off_season':
            # For post-season/off-season, fetch all weeks as we won't have new weeks
            print(f"League is in {season_status}, fetching all weeks")
            return self.fetch_all_matchups()
        
        # Get current week from league metadata
        current_week = self.league_data.get('week')
        
        if current_week is None or current_week <= 0:
            print("Could not determine current week from league data, fetching all weeks")
            return self.fetch_all_matchups()
        
        print(f"Fetching only week {current_week} from API (current active week)")
        weekly_df = self.fetch_weekly_matchups(current_week)
        
        if not weekly_df.empty:
            weekly_df['Week'] = current_week
            return weekly_df
        else:
            return pd.DataFrame()

    @staticmethod
    def display_matchups(matchups_df: pd.DataFrame, title: str = "Matchups"):
        """
        Prints a Pandas DataFrame as a clean, plain text table.

        Args:
            matchups_df (pd.DataFrame): The DataFrame to display.
            title (str): An optional title for the table.
        """
        if not matchups_df.empty:
            print(f"\n--- {title} ---")
            print(matchups_df.to_string(index=False))
        else:
            print(f"\n--- No data to display for {title} ---")

# --- Main execution to generate HTML file --- 

my_league_id = '1247641515757404160' # Replace with your actual league ID
current_week = 14 # This can be dynamically determined or set manually
base_url = 'https://api.sleeper.app/v1'

print(f"Initializing SleeperLeague for league ID: {my_league_id}")

# Traverse league history to get all seasons
league_history = []
current_league_id = my_league_id

for i in range(20):  # Safety limit
    try:
        league_endpoint = f"{base_url}/league/{current_league_id}"
        league_response = requests.get(league_endpoint)
        if league_response.status_code != 200:
            break
        league_data = league_response.json()
        
        season = league_data.get('season')
        prev_league_id = league_data.get('previous_league_id')
        
        league_history.append({
            'season': season,
            'league_id': current_league_id
        })
        
        print(f"Found season: {season}")
        
        if not prev_league_id:
            break
        
        current_league_id = prev_league_id
    except Exception as e:
        print(f"Error fetching league history: {e}")
        break

# Reverse to have oldest first, but we'll track current season separately
league_history.reverse()
most_recent_season = league_history[-1] if league_history else None

print(f"\nLeague history: {[h['season'] for h in league_history]}")
print(f"Most recent season: {most_recent_season['season'] if most_recent_season else 'Unknown'}")

# Fetch data for all seasons
all_seasons_data = {}
season_dropdown_options = []

for idx, season_info in enumerate(league_history):
    season = season_info['season']
    season_league_id = season_info['league_id']
    is_current_season = (season == most_recent_season['season'])
    
    # Try to load from cache first (except for current season)
    cached_data = None
    if not is_current_season:
        # Create a minimal SleeperLeague object first
        temp_league = SleeperLeague(season_league_id)
        cached_data = load_cached_season(season_league_id, season, temp_league)
    
    if cached_data:
        # Use cached data
        all_seasons_data[season] = cached_data
    else:
        # Fetch from API
        print(f"\nInitializing season {season}...")
        season_sleeper_league = SleeperLeague(season_league_id)
        
        if season_sleeper_league.league_data:
            if is_current_season:
                # For current season, ONLY fetch the current week from API
                print(f"Fetching ONLY current week for season {season} (optimization)")
                current_week_matchups = season_sleeper_league.fetch_current_week_matchups()
                
                # Merge with cached data from all previous weeks (if available from earlier runs)
                # For now, we'll just use the current week
                all_league_matchups = current_week_matchups
                print(f"✓ Fetched current week for season {season}")
            else:
                # For past seasons, fetch all weeks and cache them
                print(f"Fetching all weeks for past season {season}...")
                all_league_matchups = season_sleeper_league.fetch_all_matchups()
                print(f"✓ Fetched all weeks for past season {season}")
            
            season_data_to_store = {
                'league': season_sleeper_league,
                'matchups': all_league_matchups,
                'league_name': season_sleeper_league.league_data.get('name')
            }
            all_seasons_data[season] = season_data_to_store
            
            # Cache past seasons
            if not is_current_season:
                cache_payload = {
                    'league_id': season_league_id,
                    'season': season,
                    'league_name': season_sleeper_league.league_data.get('name'),
                    'matchups': all_league_matchups.to_dict('records') if isinstance(all_league_matchups, pd.DataFrame) else all_league_matchups,
                    'user_id_to_team_name': season_sleeper_league.user_id_to_team_name,
                    'team_name_to_user_id': season_sleeper_league.team_name_to_user_id
                }
                save_cached_season(season_league_id, season, cache_payload)
        else:
            print(f"Failed to fetch season {season}")
    
    if season in all_seasons_data:
        season_dropdown_options.append({
            'season': season,
            'selected': season == most_recent_season['season']
        })

# Use most recent season for initial display
if season_dropdown_options:
    most_recent_year = max(season_dropdown_options, key=lambda x: int(x['season']))['season']
else:
    most_recent_year = None

print(f"\nProcessing {len(all_seasons_data)} seasons for HTML generation...")

if most_recent_year and most_recent_year in all_seasons_data:
    my_sleeper_league = all_seasons_data[most_recent_year]['league']
    all_league_matchups = all_seasons_data[most_recent_year]['matchups']
    
    print(f"\nLeague Name: {my_sleeper_league.league_data.get('name')}")
    print(f"Total Users: {len(my_sleeper_league.user_id_to_name)}")
    print(f"Total Rosters: {len(my_sleeper_league.roster_id_to_user_id)}")

    # Generate tables for the most recent season first
    # We'll add all seasons to JavaScript below
    all_years_weekly_tables = {}  # season -> week -> html
    all_years_standings = {}  # season -> standings html
    all_years_stats = {}  # season -> stats data
    
    for season, season_data in all_seasons_data.items():
        season_league = season_data['league']
        season_matchups = season_data['matchups']
        
        # Calculate standings and stats for this season
        standings_df = calculate_standings(season_matchups)
        stats_dict = calculate_season_stats(season_matchups)
        
        # Store stats for JavaScript
        all_years_stats[season] = stats_dict
        
        # Generate standings table HTML
        if not standings_df.empty:
            standings_html = standings_df.to_html(index=False, classes='standings-table')
            standings_html = standings_html.replace('<td>', '<td class="cell">')
            standings_html = standings_html.replace('<th>', '<th class="header-cell">')
            all_years_standings[season] = f'<h3 class="standings-title">{season} Season Standings</h3>{standings_html}'
        else:
            all_years_standings[season] = '<p>No standings data available yet.</p>'
        
        weekly_html_tables = {}
        for week, week_df in season_matchups.groupby('Week'):
            week_df_display = week_df.copy()
            # Drop the Week column as it's redundant with the dropdown selector
            week_df_display = week_df_display.drop(columns=['Week'])
            if 'Matchup ID' in week_df_display.columns:
                week_df_display['Matchup ID'] = week_df_display['Matchup ID'].astype('Int64')

            # Custom HTML generation with styling
            html_table = week_df_display.to_html(index=False, classes='matchup-table')
            
            # Add CSS classes to team names and scores for better styling
            html_table = html_table.replace('<td>', '<td class="cell">')
            html_table = html_table.replace('<th>', '<th class="header-cell">')
            
            # Add winner highlighting for completed matchups
            for idx, row in week_df_display.iterrows():
                team1 = row.get('Team 1')
                team2 = row.get('Team 2')
                score1 = row.get('Score 1')
                score2 = row.get('Score 2')
                
                # Only highlight if it's a real matchup (not bye/incomplete)
                if team1 not in ['BYE', 'UNPLAYED/INCOMPLETE'] and team2 not in ['BYE', 'UNPLAYED/INCOMPLETE']:
                    winner = determine_matchup_winner(score1, score2)
                    
                    if winner == 1:  # Team 1 wins
                        # Highlight team 1 and score 1
                        html_table = html_table.replace(
                            f'<td class="cell team-name">{team1}</td>',
                            f'<td class="cell team-name winner">🏆 {team1}</td>',
                            1
                        )
                        html_table = html_table.replace(
                            f'<td class="cell">{score1}</td>',
                            f'<td class="cell winner-score">{score1}</td>',
                            1
                        )
                    elif winner == 2:  # Team 2 wins
                        # Highlight team 2 and score 2
                        html_table = html_table.replace(
                            f'<td class="cell team-name">{team2}</td>',
                            f'<td class="cell team-name winner">🏆 {team2}</td>',
                            1
                        )
                        html_table = html_table.replace(
                            f'<td class="cell">{score2}</td>',
                            f'<td class="cell winner-score">{score2}</td>',
                            1
                        )
            
            # Wrap team names in links to Sleeper user profiles, BEFORE other replacements
            # Get the list of team names from this week's data to identify them in the HTML
            team_names_in_week = set()
            for _, row in week_df_display.iterrows():
                if pd.notna(row.get('Team 1')) and row['Team 1'] not in ['BYE', 'UNPLAYED/INCOMPLETE']:
                    team_names_in_week.add(str(row['Team 1']))
                if pd.notna(row.get('Team 2')) and row['Team 2'] not in ['BYE', 'UNPLAYED/INCOMPLETE']:
                    team_names_in_week.add(str(row['Team 2']))
            
            # Replace each team name with a clickable link to their Sleeper profile
            for team_name in team_names_in_week:
                user_id = season_league.team_name_to_user_id.get(team_name)
                # Handle both winner and non-winner cases
                patterns = [
                    f'<td class="cell team-name winner">🏆 {team_name}</td>',
                    f'<td class="cell team-name">{team_name}</td>'
                ]
                
                if user_id:
                    sleeper_user_url = f"https://sleeper.app/user/{user_id}"
                    for pattern in patterns:
                        if pattern in html_table:
                            new_cell = pattern.replace(
                                f'>{team_name}</a>',
                                f'><a href="{sleeper_user_url}" target="_blank">{team_name}</a>',
                                1
                            )
                            # Remove old closing tag and add link
                            new_cell = pattern.replace(
                                f'>{team_name}<',
                                f'><a href="{sleeper_user_url}" target="_blank">{team_name.replace("🏆 ", "")}</a><',
                                1
                            )
                            # Simpler approach: wrap in link properly
                            team_display = f'🏆 {team_name}' if '🏆' in pattern else team_name
                            if '🏆' in pattern:
                                new_cell = f'<td class="cell team-name winner"><a href="{sleeper_user_url}" target="_blank">🏆 {team_name}</a></td>'
                            else:
                                new_cell = f'<td class="cell team-name"><a href="{sleeper_user_url}" target="_blank">{team_name}</a></td>'
                            html_table = html_table.replace(pattern, new_cell, 1)
            
            # Replace column headers with styled versions
            html_table = html_table.replace('<th class="header-cell">Team 1</th>', '<th class="header-cell team-name">Team 1</th>')
            html_table = html_table.replace('<th class="header-cell">Team 2</th>', '<th class="header-cell team-name">Team 2</th>')
            html_table = html_table.replace('<th class="header-cell">Score 1</th>', '<th class="header-cell score">Score 1</th>')
            html_table = html_table.replace('<th class="header-cell">Score 2</th>', '<th class="header-cell score">Score 2</th>')
            
            # Add bye week styling
            html_table = html_table.replace('>BYE<', ' class="bye-week">BYE<')
            html_table = html_table.replace('>UNPLAYED/INCOMPLETE<', ' class="bye-week">UNPLAYED/INCOMPLETE<')
            html_table = html_table.replace('>N/A<', ' class="bye-week">N/A<')

            weekly_html_tables[int(week)] = html_table
        
        all_years_weekly_tables[season] = weekly_html_tables
        print(f"Generated {len(weekly_html_tables)} HTML tables for season {season}")

        # Dynamically determine the active week for display for this season
        dynamic_current_week = 1 # Default to week 1 if no other week is found

        all_present_weeks = sorted(season_matchups['Week'].unique())

        for week in reversed(all_present_weeks):
            week_data = season_matchups[season_matchups['Week'] == week]

            # Condition 1: Check if this week contains any matchup that is NOT 'UNPLAYED/INCOMPLETE'
            has_some_real_matchups = not (week_data['Team 2'] == 'UNPLAYED/INCOMPLETE').all()

            if has_some_real_matchups:
                # Condition 2: Check if there's any non-zero score in this week
                scores1_numeric = pd.to_numeric(week_data['Score 1'], errors='coerce')
                scores2_numeric = pd.to_numeric(week_data['Score 2'], errors='coerce')

                has_non_zero_scores = (scores1_numeric > 0).any() or (scores2_numeric > 0).any()

                if has_non_zero_scores:
                    dynamic_current_week = week
                    break # Found the active week with actual scores
                else:
                    print(f"DEBUG: Week {week} has real matchups but all scores are zero. Skipping for active week determination.")

    active_week_for_display = dynamic_current_week
    print(f"Dynamically determined active week for display: {active_week_for_display}")
    last_scored_week = active_week_for_display # Use for JS default

    # --- Generate HTML Structure with Timestamp ---
    current_utc_time = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')

    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>JTL Weekly Matchups</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #013369 0%, #1a4d8f 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1000px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            padding: 40px;
        }}
        
        h1 {{
            color: #013369;
            margin-bottom: 30px;
            text-align: center;
            font-size: 2.5em;
            background: linear-gradient(135deg, #013369 0%, #d50a0a 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}
        
        .controls {{
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 15px;
            margin-bottom: 30px;
            flex-wrap: wrap;
        }}
        
        label {{
            font-weight: 600;
            color: #555;
            font-size: 1.1em;
        }}
        
        select {{
            padding: 10px 15px;
            font-size: 1em;
            border: 2px solid #013369;
            border-radius: 8px;
            background: white;
            cursor: pointer;
            transition: all 0.3s ease;
            min-width: 150px;
        }}
        
        select:hover {{
            border-color: #d50a0a;
            box-shadow: 0 4px 12px rgba(213, 10, 10, 0.2);
        }}
        
        select:focus {{
            outline: none;
            border-color: #d50a0a;
            box-shadow: 0 0 0 3px rgba(213, 10, 10, 0.1);
        }}
        
        #matchupContainer {{
            margin-top: 30px;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 0;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            border-radius: 8px;
            overflow: hidden;
        }}
        
        thead {{
            background: linear-gradient(135deg, #013369 0%, #d50a0a 100%);
            color: white;
        }}
        
        th {{
            padding: 18px;
            text-align: left;
            font-weight: 700;
            font-size: 1.05em;
            letter-spacing: 0.5px;
        }}
        
        td {{
            padding: 16px 18px;
            border-bottom: 1px solid #e0e0e0;
            font-size: 1em;
            color: #333;
        }}
        
        tbody tr {{
            transition: all 0.2s ease;
        }}
        
        tbody tr:hover {{
            background-color: #f5f5f5;
            transform: scale(1.01);
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        }}
        
        tbody tr:last-child td {{
            border-bottom: none;
        }}
        
        tbody tr:nth-child(odd) {{
            background-color: #fafafa;
        }}
        
        .team-name {{
            font-weight: 600;
            color: #013369;
        }}
        
        .team-name a {{
            color: #013369;
            text-decoration: none;
            border-bottom: 2px solid #d50a0a;
            transition: all 0.2s ease;
            cursor: pointer;
        }}
        
        .team-name a:hover {{
            color: #d50a0a;
            border-bottom-color: #013369;
        }}
        
        .score {{
            font-weight: 700;
            font-size: 1.15em;
        }}
        
        .bye-week {{
            color: #999;
            font-style: italic;
        }}
        
        .winner {{
            background-color: #fff3cd;
            font-weight: 700;
            color: #d50a0a;
        }}
        
        .winner-score {{
            background-color: #fff3cd;
            font-weight: 700;
            color: #d50a0a;
            font-size: 1.1em;
        }}
        
        .season-stats {{
            margin: 30px 0;
            padding: 20px;
            background: #f9f9f9;
            border-left: 4px solid #d50a0a;
            border-radius: 4px;
        }}
        
        .season-stats h3 {{
            color: #013369;
            margin-bottom: 15px;
            font-size: 1.3em;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
        }}
        
        .stat-box {{
            background: white;
            padding: 15px;
            border-radius: 6px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }}
        
        .stat-label {{
            color: #666;
            font-size: 0.9em;
            font-weight: 600;
            margin-bottom: 5px;
        }}
        
        .stat-value {{
            color: #d50a0a;
            font-size: 1.8em;
            font-weight: 700;
        }}
        
        .standings-table {{
            margin: 30px 0;
            width: 100%;
        }}
        
        .standings-title {{
            color: #013369;
            font-size: 1.5em;
            font-weight: 700;
            margin: 30px 0 15px 0;
            padding-bottom: 10px;
            border-bottom: 2px solid #d50a0a;
        }}
        
        .info-tabs {{
            display: flex;
            gap: 10px;
            margin: 20px 0;
            flex-wrap: wrap;
        }}
        
        .tab-button {{
            padding: 10px 20px;
            border: 2px solid #013369;
            background: white;
            color: #013369;
            cursor: pointer;
            border-radius: 6px;
            font-weight: 600;
            transition: all 0.3s ease;
        }}
        
        .tab-button.active {{
            background: #013369;
            color: white;
        }}
        
        .tab-button:hover {{
            background: #d50a0a;
            border-color: #d50a0a;
            color: white;
        }}
        
        .tab-content {{
            display: none;
        }}
        
        .tab-content.active {{
            display: block;
        }}
        
        .footer {{
            margin-top: 40px;
            text-align: center;
            color: #888;
            font-size: 0.9em;
            padding-top: 20px;
            border-top: 1px solid #e0e0e0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>JTL Weekly Matchups</h1>
        <div class="controls">
            <label for="yearSelector">Select Year:</label>
            <select id="yearSelector"></select>
            <label for="weekSelector">Select Week:</label>
            <select id="weekSelector"></select>
        </div>
        
        <!-- Tab buttons for switching views -->
        <div class="info-tabs">
            <button class="tab-button active" onclick="switchTab('matchups')">Matchups</button>
            <button class="tab-button" onclick="switchTab('standings')">Standings</button>
            <button class="tab-button" onclick="switchTab('stats')">Season Stats</button>
        </div>
        
        <!-- Matchups tab -->
        <div id="matchups" class="tab-content active">
            <div id="matchupContainer"></div>
        </div>
        
        <!-- Standings tab -->
        <div id="standings" class="tab-content">
            <div id="standingsContainer"></div>
        </div>
        
        <!-- Season Stats tab -->
        <div id="stats" class="tab-content">
            <div id="statsContainer"></div>
        </div>
        
        <div class="footer">Last Updated: {current_utc_time}</div>
    </div>
</body>
</html>
"""

    # --- Implement JavaScript for Dynamic Display ---
    js_code = f"""
<script>
    const allSeasonsWeeklyTables = {json.dumps(all_years_weekly_tables)};
    const allSeasonsStandings = {json.dumps(all_years_standings)};
    const allSeasonsStats = {json.dumps(all_years_stats)};
    const lastScoredWeek = {active_week_for_display};
    const mostRecentSeason = '{most_recent_season['season']}';

    const yearSelector = document.getElementById('yearSelector');
    const weekSelector = document.getElementById('weekSelector');
    const matchupContainer = document.getElementById('matchupContainer');
    const standingsContainer = document.getElementById('standingsContainer');
    const statsContainer = document.getElementById('statsContainer');

    // Tab switching function
    function switchTab(tabName) {{
        // Hide all tabs
        const tabs = document.querySelectorAll('.tab-content');
        tabs.forEach(tab => tab.classList.remove('active'));
        
        // Remove active class from all buttons
        const buttons = document.querySelectorAll('.tab-button');
        buttons.forEach(btn => btn.classList.remove('active'));
        
        // Show selected tab
        document.getElementById(tabName).classList.add('active');
        
        // Highlight clicked button
        event.target.classList.add('active');
        
        // Update standings and stats when those tabs are clicked
        if (tabName === 'standings') {{
            displayStandings();
        }} else if (tabName === 'stats') {{
            displayStats();
        }}
    }}

    // Populate year dropdown
    for (const season in allSeasonsWeeklyTables) {{
        const option = document.createElement('option');
        option.value = season;
        option.textContent = `{'{'}${'{season}'}{'}'} Season`;
        if (season === mostRecentSeason) {{
            option.selected = true;
        }}
        yearSelector.appendChild(option);
    }}

    // Function to update weeks when year changes
    function updateWeekSelector() {{
        weekSelector.innerHTML = '';  // Clear existing options
        const selectedYear = yearSelector.value;
        const weeksForSeason = allSeasonsWeeklyTables[selectedYear];
        
        const weeks = Object.keys(weeksForSeason).map(w => parseInt(w)).sort((a, b) => a - b);
        
        for (const week of weeks) {{
            const option = document.createElement('option');
            option.value = week;
            option.textContent = `Week ${{week}}`;
            if (parseInt(week) === lastScoredWeek && selectedYear === mostRecentSeason) {{
                option.selected = true;
            }}
            weekSelector.appendChild(option);
        }}
        
        // Display first available week
        displayWeekMatchups();
    }}

    // Function to display the selected week's matchups
    function displayWeekMatchups() {{
        const selectedYear = yearSelector.value;
        const selectedWeek = weekSelector.value;
        
        if (allSeasonsWeeklyTables[selectedYear] && allSeasonsWeeklyTables[selectedYear][selectedWeek]) {{
            matchupContainer.innerHTML = allSeasonsWeeklyTables[selectedYear][selectedWeek];
        }} else {{
            matchupContainer.innerHTML = `<p>No matchups found for Week ${{selectedWeek}} in {'{'}${{selectedYear}}{'}'}.</p>`;
        }}
    }}

    // Attach event listeners
    yearSelector.addEventListener('change', updateWeekSelector);
    weekSelector.addEventListener('change', displayWeekMatchups);

    // Function to display standings
    function displayStandings() {{
        const selectedYear = yearSelector.value;
        if (allSeasonsStandings[selectedYear]) {{
            standingsContainer.innerHTML = allSeasonsStandings[selectedYear];
        }} else {{
            standingsContainer.innerHTML = '<p>No standings available for this season.</p>';
        }}
    }}

    // Function to display season statistics
    function displayStats() {{
        const selectedYear = yearSelector.value;
        const stats = allSeasonsStats[selectedYear];
        
        if (!stats || Object.keys(stats).length === 0) {{
            statsContainer.innerHTML = '<p>No statistics available for this season.</p>';
            return;
        }}
        
        let statsHtml = `<div class="season-stats">
            <h3>{'{'}${{selectedYear}}{'}'} Season Statistics</h3>
            <div class="stats-grid">
                <div class="stat-box">
                    <div class="stat-label">Total Matchups</div>
                    <div class="stat-value">${{stats.total_matchups || 0}}</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">Average Points Per Team</div>
                    <div class="stat-value">${{stats.avg_points || 'N/A'}}</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">Highest Score</div>
                    <div class="stat-value">${{stats.highest_score || 'N/A'}}</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">Lowest Score</div>
                    <div class="stat-value">${{stats.lowest_score || 'N/A'}}</div>
                </div>
            </div>
        </div>`;
        
        statsContainer.innerHTML = statsHtml;
    }}

    // Initialize on page load
    updateWeekSelector();
</script>
"""
    html_content = html_content.replace('</body>', f'{js_code}\n</body>')

    # --- Save HTML File ---
    file_name = 'index.html'
    with open(file_name, 'w') as f:
        f.write(html_content)

    print(f"Interactive HTML file '{file_name}' generated successfully.")
else:
    print(f"\nFailed to initialize SleeperLeague for ID: {my_league_id}. Please check the league ID.")