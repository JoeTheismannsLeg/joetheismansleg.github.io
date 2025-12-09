# Joe Theismann's Leg - Fantasy Football Dashboard

A modern fantasy football dashboard for tracking league matchups, standings, and luck statistics. Built with Python and deployed automatically via GitHub Actions.

## Overview

This project fetches data from the Sleeper.app fantasy football API and generates an interactive HTML dashboard displaying:
- **Weekly matchups** with scores and results
- **Standings** with win/loss records and point totals
- **Behind the Cue Ball** - luck statistics comparing actual vs. expected performance
- **Historical data** - complete history across all seasons
- **Custom postseason matchups** - JTL-specific playoff format

## Features

- 📊 **Interactive Dashboard** - Real-time week and year selection with dynamically filtered views
- 🏆 **Comprehensive Statistics** - Track team performance, luck factor, and cumulative season trends
- 📈 **Historical Analysis** - Compare performance across multiple seasons (2019-present)
- 🔄 **Automated Deployment** - Updates on a schedule and on push via GitHub Actions
- 📱 **Responsive Design** - Works on desktop and mobile browsers
- 🎯 **Custom Postseason Format** - Support for league-specific playoff matchups

## Project Structure

### Architecture

The project is organized into three main layers:

#### 1. **Data Layer** (`src/joetheismannsleg/data/`)
Handles API communication and data fetching:
- **`LeagueClient`** - Modern API client for Sleeper.app
  - Fetches league information, rosters, and matchup data
  - Supports historical season traversal via `previous_league_id` chain
  - Robust error handling with timeout and connection management

- **`League`** - Legacy API wrapper (maintained for compatibility)

**Key Methods:**
- `fetch_season_matchups()` - Get all matchups for current season
- `fetch_season_matchups_for_year()` - Get matchups for a specific historical season
- `get_available_seasons()` - Discover all available seasons

#### 2. **Calculations Layer** (`src/joetheismannsleg/calculations/`)
Processes raw data into meaningful statistics:
- **`calculate_standings()`** - Compute win/loss records and point totals
- **`calculate_luck_stats()`** - Weekly luck metrics (actual vs. true win %)
- **`calculate_cumulative_luck_stats()`** - Season-to-date luck tracking with trend analysis
- **Data conversion** - Transform to DataFrames for display

**Behind the Cue Ball Metrics:**
- **Win %**: Actual cumulative win percentage
- **True %**: Win percentage if team played all other teams each week
- **Luck**: Difference (Win % - True %) - positive = lucky, negative = unlucky
- **Delta Luck**: Week-to-week change in luck factor
- **Trend**: Arrow indicator (↑ improving, ↓ declining, → stable)

#### 3. **UI Layer** (`src/joetheismannsleg/ui/`)
Generates interactive HTML output:
- **`generate_html()`** - Main HTML generation function
  - Converts DataFrames to styled HTML tables
  - Organizes data by year and week
  - Injects JavaScript for dynamic filtering
  - Supports both regular season and custom postseason matchups

**Features:**
- CSS styling with gradient headers and responsive tables
- JavaScript controls for year/week selection
- Tab-based interface (Matchups, Standings, Stats)
- Sortable statistics tables
- Git integration (branch/commit info in footer)

### Data Models

Located in `src/joetheismannsleg/models.py`:
- **`Matchup`** - Single matchup with teams, scores, and metadata
  - `is_bye()` - Check for bye weeks
  - `is_incomplete()` - Check for unplayed matches
  - `is_postseason()` - Identify custom postseason matchups
  - `winner()` - Determine matchup result

- **`TeamRecord`** - Team standings data (wins, losses, points)
- **`LuckStats`** - Luck statistics for a team/week
- **`LeagueInfo`** - League metadata

### Postseason Configuration

Custom postseason matchups are defined in `data/postseason_matchups.json`:

```json
{
  "2025": [
    {"name": "playoff_g1", "week": 14, "team_1": "Team A", "team_2": "Team B"},
    {"name": "playoff_g2", "week": 14, "team_1": "Team C", "team_2": "Team D"},
    ...
  ]
}
```

- **Name** - Identifier for the matchup (e.g., "playoff_g1")
- **Week** - Week number (14-17)
- **Teams** - Display names matching roster team names

## Installation

### Prerequisites
- Python 3.10+
- pip or poetry for dependency management

### Setup

```bash
# Clone the repository
git clone https://github.com/JoeTheismannsLeg/joetheismansleg.github.io.git
cd joetheismansleg.github.io

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install the package
pip install -e ".[dev]"
```

## Usage

### Running Locally

Generate the HTML dashboard:

```bash
python -m joetheismannsleg
# or
fantasy-league
```

This creates `index.html` in the current directory with:
- Current season data
- Historical data from all available seasons
- Default view to the current active week
- Full interactive functionality

### Configuration

The league is configured via environment variables or direct code modification:

```python
config = LeagueConfig(
    league_id="1247641515757404160",  # Your Sleeper league ID
    base_url="https://api.sleeper.app/v1",
    request_timeout=30,
    max_retries=3
)
```

## Deployment

### GitHub Actions

The project includes automated deployment via `.github/workflows/deploy.yml`:

**Triggers:**
- Every push to any branch
- On a schedule (currently every 5 minutes for testing)

**Process:**
1. Run tests and linting
2. Generate `index.html`
3. Deploy to GitHub Pages

**Current Schedule:**
Edit the cron expression in `.github/workflows/deploy.yml` to change update frequency.

**Note:** Cron uses UTC. Convert your timezone:
- ET to UTC: Subtract 5 hours (standard) or 4 hours (daylight)

### Environment Variables

When running in GitHub Actions, these are automatically provided:
- `GITHUB_ACTIONS` - Set to "true"
- `GITHUB_HEAD_REF` - Branch name (PRs)
- `GITHUB_REF_NAME` - Branch or tag name
- `GITHUB_SHA` - Commit SHA (for GitHub links in footer)

## Development

### Project Setup

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v --cov

# Linting and formatting
ruff check src/ tests/
black --check src/ tests/
mypy src/
```

### Adding Support for New Seasons

The system automatically discovers all historical seasons via the Sleeper API's `previous_league_id` chain. New seasons are automatically included when:
1. The Sleeper league ID changes (next season)
2. The CLI discovers the previous_league_id
3. Matchups are fetched for all discovered seasons

### Customizing Postseason Format

Edit `data/postseason_matchups.json`:

```json
{
  "2025": [
    {"name": "playoff_g1", "week": 14, "team_1": "Team Name", "team_2": "Team Name"},
    {"name": "playoff_g2", "week": 14, "team_1": "Team Name", "team_2": "Team Name"},
    ...
  ],
  "2026": [
    ...
  ]
}
```

Team names must match the display names from Sleeper rosters.

## Key Concepts

### Active Week Detection

The system automatically determines the "active week" by:
1. Scanning all weeks in reverse order
2. Finding the first week with non-zero scores
3. Checking that it's not a bye or incomplete week

This ensures the dashboard defaults to the most recent completed week.

### Luck Statistics

"Behind the Cue Ball" metrics measure league luck:
- A team that beats everyone has `luck = win% - true%` > 0 (lucky schedule)
- A team that loses to everyone has `luck < 0` (unlucky schedule)
- This helps identify overperforming and underperforming teams

### Historical Data Structure

Data is organized hierarchically:
```
League
  → Seasons (2019-2025)
    → Weeks (1-17)
      → Matchups
        → Teams, scores, results
    → Season Standings
    → Season Luck Stats
```

## Testing

Run the test suite:

```bash
pytest tests/ -v
```

Current tests verify:
- Year filtering functionality
- JSON serialization for JavaScript data
- HTML element presence and structure

## Troubleshooting

### HTML not generating
- Check that the Sleeper league ID is correct
- Verify network connectivity to api.sleeper.app
- Check GitHub Actions logs for API errors

### Missing historical data
- Ensure all league IDs in the `previous_league_id` chain are accessible
- Verify no gaps in season years

### Postseason matchups not showing
- Check team names in `postseason_matchups.json` match Sleeper exactly
- Verify JSON syntax is valid
- Ensure weeks are between 14-17

## API Reference

### Sleeper.app Endpoints Used

- `GET /league/{league_id}` - League information
- `GET /league/{league_id}/users` - Team owners and names
- `GET /league/{league_id}/rosters` - Roster information
- `GET /league/{league_id}/matchups/{week}` - Weekly matchups

## License

MIT

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request with clear descriptions

## Support

For issues, questions, or feature requests, please open an issue on GitHub.

---

**Last Updated:** December 2025  
**Current Season:** 2025  
**Available Seasons:** 2019-2025