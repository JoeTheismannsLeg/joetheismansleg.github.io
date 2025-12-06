import requests
import pandas as pd
import datetime
import json

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
            print(f"Successfully fetched user data for {len(self.user_id_to_name)} users.")
        except requests.exceptions.RequestException as e:
            print(f"Error fetching user data: {e}")
            self.users_data = None
            self.user_id_to_name = {}

        # 3. Fetch roster data
        rosters_endpoint = f"{self.base_url}/league/{self.league_id}/rosters"
        try:
            rosters_response = requests.get(rosters_endpoint)
            rosters_response.raise_for_status()
            rosters_data = rosters_response.json()
            self.roster_id_to_user_id = {}
            self.roster_id_to_team_name = {}
            for roster_entry in rosters_data:
                if roster_entry.get('owner_id'):
                    self.roster_id_to_user_id[roster_entry['roster_id']] = roster_entry['owner_id']
                    # Extract team name from metadata, fallback to display_name if not available
                    metadata = roster_entry.get('metadata', {})
                    team_name = metadata.get('team_name') if metadata else None
                    if not team_name:
                        # Fallback to user display name if team_name not set
                        user_id = roster_entry['owner_id']
                        team_name = self.user_id_to_name.get(user_id, f"Unknown Team (Roster {roster_entry['roster_id']})")
                    self.roster_id_to_team_name[roster_entry['roster_id']] = team_name
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

print(f"Initializing SleeperLeague for league ID: {my_league_id}")
my_sleeper_league = SleeperLeague(my_league_id)

if my_sleeper_league.league_data:
    print(f"\nLeague Name: {my_sleeper_league.league_data.get('name')}")
    print(f"Total Users: {len(my_sleeper_league.user_id_to_name)}")
    print(f"Total Rosters: {len(my_sleeper_league.roster_id_to_user_id)}")

    # Fetch all matchups for all 17 weeks
    all_league_matchups = my_sleeper_league.fetch_all_matchups()

    # --- Prepare Data for HTML ---
    weekly_html_tables = {}
    for week, week_df in all_league_matchups.groupby('Week'):
        week_df_display = week_df.copy()
        if 'Matchup ID' in week_df_display.columns:
            week_df_display['Matchup ID'] = week_df_display['Matchup ID'].astype('Int64')

        # Custom HTML generation with styling
        html_table = week_df_display.to_html(index=False, classes='matchup-table')
        
        # Add CSS classes to team names and scores for better styling
        html_table = html_table.replace('<td>', '<td class="cell">')
        html_table = html_table.replace('<th>', '<th class="header-cell">')
        
        # Replace column headers with styled versions
        html_table = html_table.replace('<td class="cell">Team 1</td>', '<td class="cell team-name">Team 1</td>')
        html_table = html_table.replace('<td class="cell">Team 2</td>', '<td class="cell team-name">Team 2</td>')
        html_table = html_table.replace('<td class="cell">Score 1</td>', '<td class="cell score">Score 1</td>')
        html_table = html_table.replace('<td class="cell">Score 2</td>', '<td class="cell score">Score 2</td>')
        
        # Add bye week styling
        html_table = html_table.replace('>BYE<', ' class="bye-week">BYE<')
        html_table = html_table.replace('>UNPLAYED/INCOMPLETE<', ' class="bye-week">UNPLAYED/INCOMPLETE<')
        html_table = html_table.replace('>N/A<', ' class="bye-week">N/A<')

        weekly_html_tables[int(week)] = html_table

    print(f"Generated {len(weekly_html_tables)} HTML tables for different weeks.")

    # Dynamically determine the active week for display
    dynamic_current_week = 1 # Default to week 1 if no other week is found

    all_present_weeks = sorted(all_league_matchups['Week'].unique())

    for week in reversed(all_present_weeks):
        week_data = all_league_matchups[all_league_matchups['Week'] == week]

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
    <title>Sleeper League Matchups</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
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
            color: #333;
            margin-bottom: 30px;
            text-align: center;
            font-size: 2.5em;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
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
            border: 2px solid #667eea;
            border-radius: 8px;
            background: white;
            cursor: pointer;
            transition: all 0.3s ease;
            min-width: 150px;
        }}
        
        select:hover {{
            border-color: #764ba2;
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.2);
        }}
        
        select:focus {{
            outline: none;
            border-color: #764ba2;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
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
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
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
            color: #667eea;
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
        <h1>Sleeper League Matchups</h1>
        <div class="controls">
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
    const weeklyHtmlTables = {json.dumps(weekly_html_tables)};
    const lastScoredWeek = {active_week_for_display};

    const weekSelector = document.getElementById('weekSelector');
    const matchupContainer = document.getElementById('matchupContainer');

    // Populate the dropdown
    for (const week in weeklyHtmlTables) {{
        const option = document.createElement('option');
        option.value = week;
        option.textContent = `Week ${{week}}`;
        if (parseInt(week) === lastScoredWeek) {{
            option.selected = true;
        }}
        weekSelector.appendChild(option);
    }}

    // Function to display the selected week's matchups
    function displayWeekMatchups() {{
        const selectedWeek = weekSelector.value;
        if (weeklyHtmlTables[selectedWeek]) {{
            matchupContainer.innerHTML = weeklyHtmlTables[selectedWeek];
        }} else {{
            matchupContainer.innerHTML = `<p>No matchups found for Week ${{selectedWeek}}.</p>`;
        }}
    }}

    // Attach event listener
    weekSelector.addEventListener('change', displayWeekMatchups);

    // Display initial week's matchups
    displayWeekMatchups();
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