#!/usr/bin/env python3
"""
Main script to generate the fantasy football league website.

This script fetches league data from Sleeper.app, processes matchup information,
calculates standings, and generates an interactive HTML page with week selector.
"""

import sys
import os
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from sleeper_league import SleeperLeague, calculate_standings
from sleeper_league.html import generate_matchup_html


def main():
    """Main entry point for site generation."""
    print("=" * 60)
    print("Sleeper League Fantasy Football - Site Generator")
    print("=" * 60)
    
    # Configuration
    LEAGUE_ID = '1247641515757404160'
    OUTPUT_FILE = 'index.html'
    
    try:
        # Initialize league
        print(f"\n📊 Initializing league (ID: {LEAGUE_ID})...")
        league = SleeperLeague(LEAGUE_ID)
        
        # Get current season
        current_year = datetime.now().year
        print(f"📅 Processing season {current_year}...")
        
        # Fetch matchups for current season
        print("📡 Fetching all matchups...")
        matchups_df = league.fetch_all_matchups()
        
        if matchups_df.empty:
            print("⚠️  No matchup data available for current season")
            return False
        
        print(f"✓ Fetched {len(matchups_df)} matchup records")
        
        # Calculate standings
        print("📈 Calculating standings...")
        standings_df = calculate_standings(matchups_df)
        
        if standings_df.empty:
            print("⚠️  No standings data available")
            return False
        
        print(f"✓ Calculated standings for {len(standings_df)} teams")
        
        # Generate HTML
        print(f"🎨 Generating HTML output to {OUTPUT_FILE}...")
        html_content = generate_matchup_html(
            matchups_df=matchups_df,
            standings_df=standings_df,
            league_name=league.league_data.get('name') if league.league_data else "Fantasy League",
            season=current_year
        )
        
        # Write output file
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"✓ Successfully wrote {OUTPUT_FILE}")
        print(f"✓ Generated at: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        
        print("\n" + "=" * 60)
        print("Site generation completed successfully!")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error generating site: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
