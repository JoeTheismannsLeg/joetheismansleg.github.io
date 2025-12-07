"""Command-line interface for fantasy league data fetcher."""

import logging
import sys
from pathlib import Path

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
    
    Returns:
        Exit code (0 for success, 1 for error)
    """
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        # Initialize configuration
        config = LeagueConfig(league_id='1247641515757404160')
        logger.info(f"Connecting to league {config.league_id}...")
        
        # Fetch data
        client = LeagueClient(config)
        matchups = client.fetch_season_matchups(weeks=17)
        logger.info(f"Fetched {len(matchups)} matchups")
        
        # Calculate statistics
        standings = calculate_standings(matchups)
        season_stats = calculate_season_stats(matchups)
        luck_stats = calculate_cumulative_luck_stats(matchups)
        
        logger.info(f"Calculated standings for {len(standings)} teams")
        logger.info(f"Calculated luck stats: {len(luck_stats)} records")
        
        # Generate HTML
        league_name = client.league_info.name if client.league_info else "Fantasy League"
        season = client.league_info.season if client.league_info else None
        
        html_content = generate_html(
            matchups=matchups,
            standings=standings,
            league_name=league_name,
            season=season,
            luck_stats=luck_stats,
        )
        
        # Write output
        output_file = Path("index.html")
        output_file.write_text(html_content)
        logger.info(f"Generated HTML report: {output_file}")
        
        return 0
        
    except Exception as e:
        logger.exception(f"Error generating report: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
