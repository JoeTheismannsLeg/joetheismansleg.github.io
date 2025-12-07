"""Command-line interface for fantasy league data fetcher."""

import logging
import sys
from pathlib import Path
from typing import Dict

from .config import LeagueConfig
from .data import LeagueClient
from .calculations import (
    calculate_standings,
    calculate_season_stats,
    calculate_cumulative_luck_stats,
)
from .ui import generate_html


def setup_logging() -> None:
    """Configure structured logging."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
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
        config = LeagueConfig(league_id='1247641515757404160')
        logger.info(f"Connecting to league {config.league_id}...")
        
        # Fetch current season data
        client = LeagueClient(config)
        logger.info("Fetching current season matchups...")
        matchups = client.fetch_season_matchups(weeks=17)
        logger.info(f"Fetched {len(matchups)} matchups for current season")
        
        # Calculate statistics for current season
        standings = calculate_standings(matchups)
        season_stats = calculate_season_stats(matchups)
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
                        logger.info(f"Processed {len(season_matchups)} matchups for season {season}")
                    else:
                        logger.debug(f"No matchups found for season {season}")
                except Exception as e:
                    logger.warning(f"Failed to fetch data for season {season}: {e}")
                    continue
        
        logger.info(f"Aggregated data for {len(historical_luck_stats)} seasons")
        
        # Generate HTML with historical data
        logger.info("Generating HTML report...")
        html_content = generate_html(
            matchups=matchups,
            standings=standings,
            league_name=league_name,
            season=current_season,
            luck_stats=luck_stats,
            historical_matchups=historical_matchups if len(historical_matchups) > 1 else None,
            historical_standings=historical_standings if len(historical_standings) > 1 else None,
            historical_luck_stats=historical_luck_stats if len(historical_luck_stats) > 1 else None,
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
