"""Enhanced fantasy league API wrapper with modern Python features."""

import logging
from typing import Dict, List, Optional

import pandas as pd
import requests

from ..config import LeagueConfig
from ..exceptions import APIError
from ..models import LeagueInfo, Matchup

logger = logging.getLogger(__name__)


class LeagueClient:
    """
    Modern fantasy league API client with improved error handling and type hints.

    Fetches fantasy league data from configured API with better architecture,
    logging, and error handling.
    """

    def __init__(self, config: LeagueConfig) -> None:
        """
        Initialize the API client.

        Args:
            config: LeagueConfig instance with API settings

        Raises:
            ValueError: If config is invalid
        """
        self.config = config
        self.session = requests.Session()
        self.session.timeout = config.request_timeout

        self.league_info: Optional[LeagueInfo] = None
        self.users_mapping: Dict[str, str] = {}  # user_id -> team_name
        self.rosters_mapping: Dict[int, str] = {}  # roster_id -> team_name

        logger.info(f"Initialized LeagueClient for league {config.league_id}")
        self._fetch_base_data()

    def _api_call(self, endpoint: str) -> Dict:
        """
        Make an API call with error handling.

        Args:
            endpoint: API endpoint path

        Returns:
            JSON response as dictionary

        Raises:
            APIError: If the request fails
        """
        url = f"{self.config.base_url}{endpoint}"
        try:
            response = self.session.get(url, timeout=self.config.request_timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout as e:
            raise APIError(f"API call timeout: {url}") from e
        except requests.exceptions.ConnectionError as e:
            raise APIError(f"Connection error to {url}") from e
        except requests.exceptions.HTTPError as e:
            raise APIError(f"HTTP {e.response.status_code}: {url}") from e
        except requests.exceptions.RequestException as e:
            raise APIError(f"Request failed: {e}") from e

    def _fetch_base_data(self) -> None:
        """Fetch and cache league base data."""
        try:
            league_data = self._api_call(f"/league/{self.config.league_id}")
            users_data = self._api_call(f"/league/{self.config.league_id}/users")
            rosters_data = self._api_call(f"/league/{self.config.league_id}/rosters")

            # Store league info
            self.league_info = LeagueInfo(
                league_id=self.config.league_id,
                name=league_data.get("name"),
                season=league_data.get("season"),
                status=league_data.get("status", "unknown"),
                current_week=league_data.get("week"),
            )

            # Build users mapping
            for user in users_data:
                user_id = user["user_id"]
                team_name = user.get("metadata", {}).get("team_name", user.get("display_name"))
                self.users_mapping[user_id] = team_name
                self.league_info.users[user_id] = user.get("display_name")

            # Build rosters mapping
            for roster in rosters_data:
                if roster.get("owner_id"):
                    roster_id = roster["roster_id"]
                    user_id = roster["owner_id"]
                    team_name = self.users_mapping.get(
                        user_id, f"Unknown Team (Roster {roster_id})"
                    )
                    self.rosters_mapping[roster_id] = team_name

            logger.info(
                f"Loaded league '{self.league_info.name}' with {len(self.users_mapping)} users"
            )

        except APIError as e:
            logger.error(f"Failed to fetch base data: {e}")
            raise

    def fetch_week_matchups(self, week: int) -> List[Matchup]:
        """
        Fetch matchups for a specific week.

        Args:
            week: Week number (1-17)

        Returns:
            List of Matchup objects
        """
        try:
            matchup_data = self._api_call(f"/league/{self.config.league_id}/matchups/{week}")
        except APIError as e:
            logger.warning(f"Failed to fetch week {week} matchups: {e}")
            return []

        matchups: List[Matchup] = []
        grouped = self._group_matchups(matchup_data)

        for matchup_id, teams in grouped.items():
            if len(teams) == 2:
                matchups.append(self._create_matchup_normal(week, matchup_id, teams))
            elif len(teams) == 1:
                matchups.append(self._create_matchup_bye(week, matchup_id, teams[0]))
            else:
                matchups.extend(self._create_matchup_incomplete(week, matchup_id, teams))

        return matchups

    def fetch_season_matchups(self, weeks: int = 17) -> List[Matchup]:
        """
        Fetch all matchups for the season.

        Args:
            weeks: Number of weeks to fetch (default 17)

        Returns:
            List of all Matchup objects
        """
        all_matchups: List[Matchup] = []

        for week in range(1, weeks + 1):
            matchups = self.fetch_week_matchups(week)
            all_matchups.extend(matchups)
            logger.debug(f"Fetched {len(matchups)} matchups for week {week}")

        logger.info(f"Fetched {len(all_matchups)} total matchups for {weeks} weeks")
        return all_matchups

    def get_available_seasons(self) -> List[int]:
        """
        Get all available seasons for the league by traversing league history.

        Sleeper creates a new league ID for each season, linked via previous_league_id.
        This method traverses backwards through the chain to find all historical seasons.

        Returns:
            List of season years in descending order (newest first)
        """
        try:
            available_seasons: List[int] = []
            current_league_id = self.config.league_id

            # Traverse backwards through league history
            max_iterations = 20  # Prevent infinite loops
            iterations = 0

            while current_league_id and iterations < max_iterations:
                try:
                    endpoint = f"/league/{current_league_id}"
                    data = self._api_call(endpoint)
                    season = data.get("season")

                    if season:
                        # Ensure season is an int
                        season_int = int(season) if isinstance(season, str) else season
                        available_seasons.append(season_int)
                        logger.debug(f"Found season: {season_int} (league_id: {current_league_id})")

                    # Move to previous season's league
                    current_league_id = data.get("previous_league_id")
                    iterations += 1

                except APIError as e:
                    logger.warning(f"Error fetching league {current_league_id}: {e}")
                    break

            # Return in descending order (newest seasons first)
            return sorted(available_seasons, reverse=True)

        except Exception as e:
            logger.warning(f"Failed to fetch available seasons: {e}")
            return [2025]  # Return current year as fallback

    def fetch_season_matchups_for_year(self, season: int, weeks: int = 17) -> List[Matchup]:
        """
        Fetch all matchups for a specific season year.

        This method traverses the league history to find the correct league_id for the season,
        then fetches matchups from that league.

        Args:
            season: Season year to fetch
            weeks: Number of weeks to fetch (default 17)

        Returns:
            List of all Matchup objects for that season
        """
        logger.info(f"Fetching matchups for {season} season")

        # Find the league_id for this season
        target_league_id = self._find_league_id_for_season(season)
        if not target_league_id:
            logger.warning(f"Could not find league for season {season}")
            return []

        logger.debug(f"Using league_id {target_league_id} for season {season}")

        # Temporarily store original league_id and switch to target
        original_league_id = self.config.league_id
        self.config.league_id = target_league_id

        all_matchups: List[Matchup] = []

        try:
            for week in range(1, weeks + 1):
                try:
                    matchups = self.fetch_week_matchups(week)
                    all_matchups.extend(matchups)
                except APIError as e:
                    logger.debug(f"Failed to fetch week {week} for season {season}: {e}")
                    continue

            logger.info(f"Fetched {len(all_matchups)} total matchups for {season} season")

        finally:
            # Restore original league_id
            self.config.league_id = original_league_id

        return all_matchups

    def _find_league_id_for_season(self, target_season: int) -> Optional[str]:
        """
        Find the league_id for a specific season by traversing league history.

        Args:
            target_season: The season year to find

        Returns:
            The league_id for that season, or None if not found
        """
        try:
            current_league_id = self.config.league_id
            max_iterations = 20
            iterations = 0

            while current_league_id and iterations < max_iterations:
                try:
                    endpoint = f"/league/{current_league_id}"
                    data = self._api_call(endpoint)
                    season = data.get("season")

                    # Convert season to int for comparison
                    if season:
                        season_int = int(season) if isinstance(season, str) else season
                        if season_int == target_season:
                            return current_league_id

                    # Move to previous season's league
                    current_league_id = data.get("previous_league_id")
                    iterations += 1

                except APIError:
                    break

            return None

        except Exception as e:
            logger.warning(f"Error finding league for season {target_season}: {e}")
            return None

    @staticmethod
    def _group_matchups(matchup_data: List[Dict]) -> Dict[Optional[int], List[Dict]]:
        """Group matchups by matchup_id."""
        grouped: Dict[Optional[int], List[Dict]] = {}
        for match in matchup_data:
            matchup_id = match.get("matchup_id")
            if matchup_id not in grouped:
                grouped[matchup_id] = []
            grouped[matchup_id].append(match)
        return grouped

    def _create_matchup_normal(self, week: int, matchup_id: int, teams: List[Dict]) -> Matchup:
        """Create a normal matchup object."""
        t1, t2 = teams[0], teams[1]
        return Matchup(
            matchup_id=matchup_id,
            week=week,
            team_1=self.rosters_mapping.get(t1["roster_id"], f"Unknown {t1['roster_id']}"),
            score_1=t1["points"],
            team_2=self.rosters_mapping.get(t2["roster_id"], f"Unknown {t2['roster_id']}"),
            score_2=t2["points"],
        )

    def _create_matchup_bye(self, week: int, matchup_id: int, team: Dict) -> Matchup:
        """Create a bye week matchup object."""
        return Matchup(
            matchup_id=matchup_id,
            week=week,
            team_1=self.rosters_mapping.get(team["roster_id"], f"Unknown {team['roster_id']}"),
            score_1=team["points"],
            team_2="BYE",
            score_2=0.0,
        )

    def _create_matchup_incomplete(
        self, week: int, matchup_id: Optional[int], teams: List[Dict]
    ) -> List[Matchup]:
        """Create incomplete matchup objects."""
        return [
            Matchup(
                matchup_id=matchup_id,
                week=week,
                team_1=self.rosters_mapping.get(t["roster_id"], f"Unknown {t['roster_id']}"),
                score_1=t["points"],
                team_2="UNPLAYED/INCOMPLETE",
                score_2=0.0,
            )
            for t in teams
        ]

    def to_dataframe(self, matchups: List[Matchup]) -> pd.DataFrame:
        """
        Convert matchups to pandas DataFrame.

        Args:
            matchups: List of Matchup objects

        Returns:
            DataFrame with standard columns
        """
        if not matchups:
            return pd.DataFrame()

        data = [
            {
                "Week": m.week,
                "Matchup ID": m.matchup_id,
                "Team 1": m.team_1,
                "Score 1": m.score_1,
                "Team 2": m.team_2,
                "Score 2": m.score_2,
            }
            for m in matchups
        ]

        return pd.DataFrame(data)

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.session.close()
        logger.debug("Closed API session")
