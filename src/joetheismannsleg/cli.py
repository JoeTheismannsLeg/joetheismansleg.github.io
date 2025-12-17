"""Command-line interface for fantasy league data fetcher."""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .calculations import (
    calculate_cumulative_luck_stats,
    calculate_playoff_seeding,
    calculate_season_stats,
    calculate_standings,
)
from .config import LeagueConfig
from .data import LeagueClient
from .divisions import REGULAR_SEASON_WEEKS, get_divisions_for_year
from .models import Matchup
from .ui import generate_html


def get_git_info() -> Tuple[str, str, str]:
    """
    Get current git branch and commit hash from GitHub Actions context.

    Uses environment variables set by GitHub Actions:
    - GITHUB_HEAD_REF: The branch name (for pull requests)
    - GITHUB_REF_NAME: The branch or tag name
    - GITHUB_SHA: The full commit SHA

    Returns:
        Tuple of (branch_name, short_commit_hash, full_commit_hash)
        For local builds without GitHub context, returns ("local build", "n/a", "n/a")
    """
    # Check if running in GitHub Actions
    if os.getenv("GITHUB_ACTIONS") == "true":
        # For pull requests, use GITHUB_HEAD_REF; otherwise use GITHUB_REF_NAME
        branch = os.getenv("GITHUB_HEAD_REF") or os.getenv("GITHUB_REF_NAME", "unknown")

        # Get full and short commit hash from GITHUB_SHA
        full_sha = os.getenv("GITHUB_SHA", "")
        short_sha = full_sha[:7] if full_sha else "n/a"

        return branch, short_sha, full_sha
    else:
        # Local build without GitHub Actions context
        return "local build", "n/a", "n/a"




def load_postseason_matchups(
    season: int,
    client: Optional["LeagueClient"] = None,  # type: ignore
    regular_matchups: Optional[List[Matchup]] = None,
) -> List[Matchup]:
    """
    Load postseason matchups from JSON file for a specific season.

    Args:
        season: Season year (e.g., 2025)
        client: Optional LeagueClient to resolve display names to team names
        regular_matchups: Optional list of regular season matchups to look up scores

    Returns:
        List of Matchup objects for postseason weeks with team names and scores populated from regular matchups
    """
    # Data file is now in the package data directory
    postseason_file = Path(__file__).parent / "data" / "postseason_matchups.json"

    try:
        if not postseason_file.exists():
            return []

        with open(postseason_file) as f:
            data = json.load(f)

        season_str = str(season)
        if season_str not in data:
            return []

        # Build display_name to team_name mapping from client
        display_name_to_team_name = {}
        if client:
            # client.users_mapping: user_id -> team_name
            # client.league_info.users: user_id -> display_name
            # We need to invert: display_name -> team_name
            for user_id, display_name in client.league_info.users.items():
                team_name = client.users_mapping.get(user_id)
                if team_name:
                    display_name_to_team_name[display_name] = team_name

        # Build mappings from regular matchups for score lookup
        # Map: (week, team_name) -> score
        score_map = {}
        if regular_matchups:
            for m in regular_matchups:
                score_map[(m.week, m.team_1)] = m.score_1
                score_map[(m.week, m.team_2)] = m.score_2

        matchups = []
        for entry in data[season_str]:
            week = entry["week"]
            display_name_1 = entry["team_1"]
            display_name_2 = entry["team_2"]

            # Resolve display names to team names
            team_1 = display_name_to_team_name.get(display_name_1, display_name_1)
            team_2 = display_name_to_team_name.get(display_name_2, display_name_2)

            # Look up scores using team names
            score_1 = score_map.get((week, team_1), 0.0)
            score_2 = score_map.get((week, team_2), 0.0)

            matchup = Matchup(
                matchup_id=None,  # Postseason matchups don't have API matchup_id
                week=week,
                team_1=team_1,
                score_1=score_1,
                team_2=team_2,
                score_2=score_2,
                name=entry.get("name"),  # Store the postseason matchup name
            )
            matchups.append(matchup)

        return matchups
    except Exception as e:
        logging.getLogger(__name__).warning(f"Failed to load postseason matchups: {e}")
        return []


def setup_logging() -> None:
    """Configure structured logging."""
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )


def main() -> int:
    """
    Main entry point for the CLI.

    Fetches league data from Sleeper API, calculates stats and luck metrics,
    and generates an interactive HTML report with historical data support.

    Returns:
        Exit code (0 for success, 1 for error)
    """
    setup_logging()
    logger = logging.getLogger(__name__)

    try:
        # Initialize configuration
        config = LeagueConfig(league_id="1247641515757404160")
        logger.info(f"Connecting to league {config.league_id}...")

        # Fetch current season data
        client = LeagueClient(config)
        logger.info("Fetching current season matchups...")
        matchups = client.fetch_season_matchups(weeks=17)
        logger.info(f"Fetched {len(matchups)} matchups for current season")

        # Calculate statistics for current season
        standings = calculate_standings(matchups)
        luck_stats = calculate_cumulative_luck_stats(matchups)

        logger.info(f"Calculated standings for {len(standings)} teams")
        logger.info(f"Calculated luck stats: {len(luck_stats)} records")

        # Get current season info (convert to int for consistency)
        league_name = client.league_info.name if client.league_info else "Fantasy League"
        current_season_str = client.league_info.season if client.league_info else None
        current_season = int(current_season_str) if current_season_str else None

        # Fetch historical data for all available seasons
        logger.info("Discovering available seasons...")
        available_seasons = client.get_available_seasons()
        logger.info(f"Found {len(available_seasons)} available seasons: {available_seasons}")

        # Helper function to calculate seeding for a given year
        def calculate_seeding_for_year(year: int, year_matchups: list, league_client):
            """Calculate playoff seeding for a given year."""
            try:
                # Build username to team mapping
                username_to_team = {}
                for user_id, display_name in league_client.league_info.users.items():
                    team_name = league_client.users_mapping.get(user_id)
                    if team_name:
                        username_to_team[display_name] = team_name
                
                # Get division assignments for this year
                boats_teams, hoes_teams = get_divisions_for_year(year, username_to_team)
                
                if boats_teams and hoes_teams:
                    # Filter to regular season only
                    regular_season_matchups = [m for m in year_matchups if m.week in REGULAR_SEASON_WEEKS]
                    
                    if regular_season_matchups:
                        return calculate_playoff_seeding(
                            regular_season_matchups,
                            boats_teams,
                            hoes_teams
                        )
            except Exception as e:
                logger.debug(f"Could not calculate seeding for {year}: {e}")
            return None, None

        # Aggregate all data by season (matchups, standings, luck stats, seeding)
        historical_matchups: Dict[int, list] = {current_season: matchups}
        historical_standings: Dict[int, list] = {current_season: standings}
        historical_luck_stats: Dict[int, list] = {current_season: luck_stats}
        historical_playoff_seeds: Dict[int, list] = {}
        historical_consolation_seeds: Dict[int, list] = {}
        
        # Calculate seeding for current season
        playoff_seeds, consolation_seeds = calculate_seeding_for_year(current_season, matchups, client)
        if playoff_seeds and consolation_seeds:
            historical_playoff_seeds[current_season] = playoff_seeds
            historical_consolation_seeds[current_season] = consolation_seeds
            logger.info("\n" + "=" * 80)
            logger.info(f"{current_season} PLAYOFF SEEDING (Based on Weeks 1-13)")
            logger.info("=" * 80)
            for seed in playoff_seeds:
                logger.info(
                    f"Seed #{seed['seed']}: {seed['team']} ({seed['wins']}-{seed['losses']}) "
                    f"- {seed['points_for']:.2f} PF [{seed['division']} {seed['seed_type']}]"
                )
            logger.info("\nCONSOLATION BRACKET:")
            for seed in consolation_seeds:
                logger.info(
                    f"Seed #{seed['seed']}: {seed['team']} ({seed['wins']}-{seed['losses']}) "
                    f"- {seed['points_for']:.2f} PF [{seed['division']}]"
                )
            logger.info("=" * 80)

        for season in available_seasons:
            if season == current_season:
                # Already have current season data
                continue
            else:
                try:
                    logger.debug(f"Fetching data for season {season}...")
                    season_matchups = client.fetch_season_matchups_for_year(season, weeks=17)
                    if season_matchups:
                        season_standings = calculate_standings(season_matchups)
                        season_luck_stats = calculate_cumulative_luck_stats(season_matchups)
                        historical_matchups[season] = season_matchups
                        historical_standings[season] = season_standings
                        historical_luck_stats[season] = season_luck_stats
                        
                        # Calculate seeding for this season
                        season_playoff_seeds, season_consolation_seeds = calculate_seeding_for_year(
                            season, season_matchups, client
                        )
                        if season_playoff_seeds and season_consolation_seeds:
                            historical_playoff_seeds[season] = season_playoff_seeds
                            historical_consolation_seeds[season] = season_consolation_seeds
                        
                        logger.info(
                            f"Processed {len(season_matchups)} matchups for season {season}"
                        )
                    else:
                        logger.debug(f"No matchups found for season {season}")
                except Exception as e:
                    logger.warning(f"Failed to fetch data for season {season}: {e}")
                    continue

        logger.info(f"Aggregated data for {len(historical_luck_stats)} seasons")

        # Get git information
        git_branch, git_commit, git_commit_full = get_git_info()
        if git_branch and git_commit != "n/a":
            logger.info(f"Git branch: {git_branch}, commit: {git_commit}")
        else:
            logger.debug("Running in local build mode (no GitHub Actions context)")

        # Load postseason matchups for current season
        logger.info("Loading postseason matchups...")
        postseason_matchups = load_postseason_matchups(current_season, client=client, regular_matchups=matchups)
        logger.info(f"Loaded {len(postseason_matchups)} postseason matchups")

        # Merge postseason matchups with regular matchups
        all_matchups = matchups + postseason_matchups

        # Generate HTML with historical data
        logger.info("Generating HTML report...")
        # Only pass historical data that excludes current season (current season is passed separately)
        historical_matchups_only = {
            year: mups for year, mups in historical_matchups.items() if year != current_season
        }
        historical_standings_only = {
            year: standings_list
            for year, standings_list in historical_standings.items()
            if year != current_season
        }
        historical_luck_stats_only = {
            year: stats for year, stats in historical_luck_stats.items() if year != current_season
        }

        html_content = generate_html(
            matchups=all_matchups,
            standings=standings,
            league_name=league_name,
            season=current_season,
            luck_stats=luck_stats,
            historical_matchups=historical_matchups_only if len(historical_matchups_only) > 0 else None,
            historical_standings=historical_standings_only if len(historical_standings_only) > 0 else None,
            historical_luck_stats=historical_luck_stats_only if len(historical_luck_stats_only) > 0 else None,
            historical_playoff_seeds=historical_playoff_seeds if len(historical_playoff_seeds) > 0 else None,
            historical_consolation_seeds=historical_consolation_seeds if len(historical_consolation_seeds) > 0 else None,
            git_branch=git_branch,
            git_commit=git_commit,
            git_commit_full=git_commit_full,
        )

        # Write output
        output_file = Path("index.html")
        output_file.write_text(html_content)
        logger.info(f"Generated HTML report: {output_file}")
        logger.info(f"Report includes {len(historical_luck_stats)} seasons of data")

        return 0

    except Exception as e:
        logger.exception(f"Error generating report: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
