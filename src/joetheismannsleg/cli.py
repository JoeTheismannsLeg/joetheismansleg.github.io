"""Command-line interface for fantasy league data fetcher."""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .calculations import (
    calculate_cumulative_luck_stats,
    calculate_season_stats,
    calculate_standings,
)
from .config import LeagueConfig
from .data import LeagueClient
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




def load_postseason_matchups(season: int) -> List[Matchup]:
    """
    Load postseason matchups from JSON file for a specific season.

    Args:
        season: Season year (e.g., 2025)

    Returns:
        List of Matchup objects for postseason weeks
    """
    postseason_file = Path(__file__).parent.parent.parent / "data" / "postseason_matchups.json"

    try:
        if not postseason_file.exists():
            return []

        with open(postseason_file) as f:
            data = json.load(f)

        season_str = str(season)
        if season_str not in data:
            return []

        matchups = []
        for entry in data[season_str]:
            matchup = Matchup(
                matchup_id=None,  # Postseason matchups don't have API matchup_id
                week=entry["week"],
                team_1=entry["team_1"],
                score_1=0.0,  # Scores will be set later when data is available
                team_2=entry["team_2"],
                score_2=0.0,
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

        # Aggregate all data by season (matchups, standings, luck stats)
        historical_matchups: Dict[int, list] = {current_season: matchups}
        historical_standings: Dict[int, list] = {current_season: standings}
        historical_luck_stats: Dict[int, list] = {current_season: luck_stats}

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
        postseason_matchups = load_postseason_matchups(current_season)
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
