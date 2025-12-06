# Copilot Instructions for joetheismansleg.github.io

## Project Overview
A GitHub Pages site that displays NFL fantasy football league matchups from Sleeper.app. The site is built using Python and deployed automatically via GitHub Actions on scheduled intervals and pushes.

## Architecture

### Core Components
- **`generate_matchup_table.py`** - Main data pipeline that:
  1. Fetches league data from Sleeper API (`SleeperLeague` class)
  2. Processes weekly matchup data (handles bye weeks and unplayed matchups)
  3. Generates interactive HTML with week selector dropdown
  4. Writes output to `index.html`

- **`generate_site.py`** - Simple HTML generation (currently unused, in favor of matchup table)

- **`.github/workflows/deploy.yml`** - GitHub Actions workflow that:
  - Runs on all pushes and on a schedule (Saturdays 2-3pm ET for testing)
  - Sets up Python 3.12, installs dependencies from `requirements.txt`
  - Executes `generate_matchup_table.py` and deploys to GitHub Pages

## Key Patterns & Conventions

### Sleeper API Integration
- Uses `requests` library to call https://api.sleeper.app/v1
- League ID: hardcoded in main script (`'1247641515757404160'`)
- Data hierarchy: League → Users → Rosters → Weekly Matchups
- Handles missing data gracefully with try/except and defensive null checks

### HTML Generation
- Uses Pandas DataFrames to organize matchup data
- Embeds JavaScript for dynamic week selection (week dropdown persists across all weeks)
- Timestamp added as "Last Updated" in UTC
- Table styling relies on default Pandas `to_html()` output

### Error Handling Philosophy
- API failures return empty DataFrames rather than raising exceptions
- Print statements used for debugging/logging (visible in GitHub Actions logs)
- Unplayed weeks marked as `'UNPLAYED/INCOMPLETE'` in Team 2 column

### Data Processing Details
- Weeks always iterate 1-17 (full season)
- Active week detection: scans backwards through weeks to find first with non-zero scores and real matchups
- Bye weeks show `'BYE'` in Team 2 with `'N/A'` score
- Matchup grouping by `matchup_id` handles multiple teams in one matchup entry

## Development Workflow

### Running Locally
```bash
python generate_matchup_table.py  # Generates index.html
```

### Dependencies
- `pandas` - DataFrame manipulation and HTML conversion
- `requests` - HTTP API calls
- `datetime` - UTC timestamp generation
- Python 3.12 (per workflow)

### Scheduling & Triggers
- Cron expression: `*/5 19-20 * * 6` (every 5 min Saturday 2-3pm ET, currently active for testing)
- Multiple commented-out schedules exist for different update frequencies
- All pushes to any branch trigger the workflow

## Common Tasks

### Adding a New Data Source
1. Extend `SleeperLeague._fetch_base_data()` or add new methods
2. Process data into DataFrame format
3. Integrate into HTML generation before `to_html()` conversion

### Changing Display Schedule
Edit `.github/workflows/deploy.yml` cron expression. Remember:
- Cron uses UTC time
- ET to UTC: subtract 5 hours (standard) or 4 hours (daylight)

### Debugging API Issues
- Check league ID validity in Sleeper app
- Print statements in `SleeperLeague` class methods are logged in Actions
- Return empty DataFrames on error to prevent workflow failure
