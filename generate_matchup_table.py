import requests
import pandas as pd
import datetime
import json
import re

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

for season_info in league_history:
    season = season_info['season']
    season_league_id = season_info['league_id']
    
    print(f"\nFetching data for season {season}...")
    season_sleeper_league = SleeperLeague(season_league_id)
    
    if season_sleeper_league.league_data:
        all_league_matchups = season_sleeper_league.fetch_all_matchups()
        all_seasons_data[season] = {
            'league': season_sleeper_league,
            'matchups': all_league_matchups,
            'league_name': season_sleeper_league.league_data.get('name')
        }
        season_dropdown_options.append({
            'season': season,
            'selected': season == most_recent_season['season']
        })
    else:
        print(f"Failed to fetch season {season}")

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
    
    for season, season_data in all_seasons_data.items():
        season_league = season_data['league']
        season_matchups = season_data['matchups']
        
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
                if user_id:
                    sleeper_user_url = f"https://sleeper.app/user/{user_id}"
                    old_cell = f'<td class="cell">{team_name}</td>'
                    new_cell = f'<td class="cell team-name"><a href="{sleeper_user_url}" target="_blank">{team_name}</a></td>'
                    html_table = html_table.replace(old_cell, new_cell)
                else:
                    # Fallback: no link if we can't find the user ID
                    old_cell = f'<td class="cell">{team_name}</td>'
                    new_cell = f'<td class="cell team-name">{team_name}</td>'
                    html_table = html_table.replace(old_cell, new_cell)
            
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
        <div id="matchupContainer"></div>
        <div class="footer">Last Updated: {current_utc_time}</div>
    </div>
</body>
</html>
"""

    # --- Implement JavaScript for Dynamic Display ---
    js_code = f"""
<script>
    const allSeasonsWeeklyTables = {json.dumps(all_years_weekly_tables)};
    const lastScoredWeek = {active_week_for_display};
    const mostRecentSeason = '{most_recent_season['season']}';

    const yearSelector = document.getElementById('yearSelector');
    const weekSelector = document.getElementById('weekSelector');
    const matchupContainer = document.getElementById('matchupContainer');

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