"""Sleeper League API wrapper for fetching fantasy football league data."""

import requests
import pandas as pd


class SleeperLeague:
    """
    A class to interact with the Sleeper API for a specific fantasy football league.
    Encapsulates methods for fetching league details, user data, roster data,
    and matchup information.
    """

    def __init__(self, league_id: str, base_url: str = 'https://api.sleeper.app/v1'):
        """
        Initialize the SleeperLeague instance.
        
        Args:
            league_id (str): The Sleeper league ID
            base_url (str): The base URL for the Sleeper API
        """
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
            return  # Exit if league data cannot be fetched

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
            return pd.DataFrame()  # Return empty DataFrame on error

        matchup_details = []
        matchups_grouped = {}
        for match in matchup_data:
            matchup_id = match['matchup_id']
            if matchup_id not in matchups_grouped:
                matchups_grouped[matchup_id] = []
            matchups_grouped[matchup_id].append(match)

        for matchup_id, teams in matchups_grouped.items():
            if len(teams) == 2:  # Normal matchup
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
            elif len(teams) == 1:  # Bye week
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
            else:  # Handle incomplete/unplayed matchups
                for team in teams:
                    team_name = self._get_team_name(team['roster_id'])
                    team_score = team['points']
                    matchup_details.append({
                        'Matchup ID': matchup_id,
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

        # Always iterate through 17 weeks
        num_total_weeks = 17

        all_matchups_dfs = []
        for week in range(1, num_total_weeks + 1):
            weekly_df = self.fetch_weekly_matchups(week)
            if not weekly_df.empty:
                weekly_df['Week'] = week  # Add a 'Week' column
                all_matchups_dfs.append(weekly_df)

        if all_matchups_dfs:
            return pd.concat(all_matchups_dfs, ignore_index=True)
        else:
            return pd.DataFrame()

    def fetch_current_week_matchups(self) -> pd.DataFrame:
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
