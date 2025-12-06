#!/usr/bin/env python3
"""Modern entry point with dependency injection and configuration."""

import logging
import sys
from datetime import datetime
from pathlib import Path

from src.sleeper_league.config import LeagueConfig
from src.sleeper_league.client import SleeperLeagueClient
from src.sleeper_league.stats_v2 import (
    calculate_standings,
    calculate_season_stats,
    standings_to_dataframe,
)
from src.sleeper_league.html_v2 import generate_html
from src.sleeper_league.exceptions import SleeperLeagueError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main() -> int:
    """
    Main entry point with modern error handling.
    
    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        logger.info("Starting Sleeper League site generation")
        
        # Configuration
        config = LeagueConfig(
            league_id='1247641515757404160',
            cache_dir=Path('.cache'),
            request_timeout=30,
        )
        
        # Fetch data
        with SleeperLeagueClient(config) as client:
            logger.info(f"Fetching data for {client.league_info.name or 'unknown league'}")
            
            matchups = client.fetch_season_matchups(weeks=17)
            
            if not matchups:
                logger.error("No matchups found")
                return 1
            
            logger.info(f"Successfully fetched {len(matchups)} matchups")
        
        # Convert to DataFrame for compatibility
        matchups_df = client.to_dataframe(matchups)
        
        # Calculate statistics
        standings = calculate_standings(matchups)
        stats = calculate_season_stats(matchups)
        
        logger.info(f"Calculated standings for {len(standings)} teams")
        logger.info(f"Season stats: {stats.total_matchups} matchups, {stats.avg_points:.1f} avg points")
        
        # Generate HTML
        html = generate_html(
            matchups=matchups,
            standings=standings,
            league_name=client.league_info.name or "Fantasy League",
            season=client.league_info.season or datetime.now().year,
        )
        
        # Write output
        output_file = Path('index.html')
        output_file.write_text(html, encoding='utf-8')
        logger.info(f"Successfully wrote {output_file}")
        
        return 0
        
    except SleeperLeagueError as e:
        logger.error(f"Sleeper League error: {e}")
        return 1
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
