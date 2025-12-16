# Copilot Instructions for joetheismansleg.github.io

## Project Overview
A GitHub Pages fantasy football dashboard that fetches data from Sleeper.app and generates an interactive HTML site with matchups, standings, and luck statistics ("Behind the Cue Ball"). Built as a Python package and deployed automatically via GitHub Actions.

## Architecture (3-Layer Design)

### 1. Data Layer (`src/joetheismannsleg/data/`)
**Primary Client: `LeagueClient`** (modern, preferred)
- Fetches from Sleeper API v1 (`https://api.sleeper.app/v1`)
- Uses `LeagueConfig(league_id="1247641515757404160")` for initialization
- Key methods:
  - `fetch_week_matchups(week)` - Single week data
  - `fetch_season_matchups()` - All weeks (1-17)
  - `fetch_season_matchups_for_year(year)` - Historical seasons via `previous_league_id` chain
  - `get_available_seasons()` - Discover all linked seasons
- **Error handling:** Raises `APIError` on failures; uses `requests.Session` with timeout (30s default)
- **Data mappings:** Caches `users_mapping` (user_id→team_name) and `rosters_mapping` (roster_id→team_name)

**Legacy: `League`** (maintained for compatibility, avoid for new code)

### 2. Calculations Layer (`src/joetheismannsleg/calculations/stats.py`)
Processes matchups into statistics:
- `calculate_standings(matchups)` → `List[TeamRecord]` (wins, losses, PF, PA)
- `calculate_luck_stats(matchups)` → Weekly luck metrics (Win % vs True %)
- `calculate_cumulative_luck_stats(matchups)` → Season-to-date with trends (↑↓→)
- **Luck formula:** Compares actual win% to win% if team played all opponents each week
- Returns DataFrames for UI consumption via `standings_to_dataframe()`

### 3. UI Layer (`src/joetheismannsleg/ui/html.py`)
`generate_html(all_matchups, output_path)`:
- Creates multi-year, multi-week dashboard with JavaScript tab switching
- Uses Pandas `.to_html()` for table generation
- Injects CSS gradients, responsive styling, and sortable tables
- Embeds git metadata in footer (branch/commit via GitHub Actions env vars)

## Data Models (`src/joetheismannsleg/models.py`)
```python
Matchup:  # Core unit
  - matchup_id, week, team_1, score_1, team_2, score_2, name (for postseason)
  - Methods: is_bye(), is_incomplete(), is_postseason(), winner()
  
TeamRecord:  # Standings
  - team, wins, losses, points_for, points_against
  
LuckStats:   # Behind the Cue Ball
  - team, week, actual_wins, possible_wins, actual_win_pct, true_win_pct
```

## Postseason Configuration
Custom playoff matchups in `data/postseason_matchups.json`:
```json
{
  "2025": [
    {"name": "playoff_g1", "week": 14, "team_1": "Team A", "team_2": "Team B"}
  ]
}
```
- Loaded via `src/joetheismannsleg/data/postseason_matchups.json` (packaged via `MANIFEST.in`)
- Matchups with `name` field are treated as postseason (`Matchup.is_postseason()`)

## Development Workflow

### Running Locally
```bash
# Install as editable package
pip install -e .

# Generate site (writes index.html to workspace root)
fantasy-league

# With dev tools
pip install -e ".[dev]"
pytest tests/ -v --cov=src/joetheismannsleg
ruff check src/ tests/
black src/ tests/
```

### CLI Entry Point (`src/joetheismannsleg/cli.py`)
- Command: `fantasy-league` (defined in `pyproject.toml` [project.scripts])
- Orchestrates: Config → LeagueClient → fetch all seasons → calculations → HTML generation
- Git info from env vars: `GITHUB_HEAD_REF`, `GITHUB_REF_NAME`, `GITHUB_SHA`

### CI/CD (`.github/workflows/deploy.yml`)
Two jobs:
1. **test**: pytest with coverage, ruff/black linting (continue-on-error), mypy type checking
2. **build**: Installs package, runs `fantasy-league`, uploads `index.html` as Pages artifact
3. **deploy**: Publishes to GitHub Pages

**Schedule:** `*/5 * * * *` (every 5 min, currently very frequent for testing)
- Cron uses UTC; convert ET by subtracting 5 hours (standard time)
- Triggered on all pushes to any branch (`branches: ["**"]`)

## Key Patterns & Conventions

### API Data Flow
1. `LeagueClient` fetches league info → builds user/roster mappings
2. Fetches matchups week-by-week → groups by `matchup_id`
3. Handles edge cases:
   - **Bye weeks:** 1 team in matchup → `team_2="BYE"`, `score_2="N/A"`
   - **Incomplete:** Non-zero matchup count ≠ 2 → `team_2="UNPLAYED/INCOMPLETE"`
   - **Historical seasons:** Traverses `previous_league_id` chain with max 20 iterations

### Error Handling Philosophy
- **Data layer:** Raises `APIError` (custom exception) on network failures
- **Calculations layer:** Returns empty lists/DataFrames on invalid input
- **Logging:** Uses Python `logging` module (visible in GitHub Actions logs)
- **Defensive coding:** Null checks for API responses (users, rosters may be missing)

### Testing
- `tests/test_json_serialization.py` - Validates postseason JSON loading
- `tests/test_year_filtering.py` - Tests multi-season data filtering
- Run with coverage: `pytest -v --cov=src/joetheismannsleg --cov-report=term-missing`

**API Mocking Strategy:**
- Mock `requests.Session.get()` or `LeagueClient._api_call()` for unit tests
- Use `pytest.fixture` to provide sample API responses (league, users, rosters, matchups)
- Test edge cases: empty responses, missing fields, network timeouts (`APIError`)
- For integration tests, consider recording real API responses with `responses` library
- Mock `LeagueConfig` with test league IDs to avoid hitting production API

### Package Configuration
- `pyproject.toml`: Uses setuptools build backend, Python ≥3.10
- `MANIFEST.in`: Includes `data/postseason_matchups.json` in package
- `src/` layout with namespace package `joetheismannsleg`
- Dev dependencies: pytest, black, ruff, mypy (optional-dependencies.dev)

## Common Tasks

### Adding New Statistic
1. Create calculation function in `src/joetheismannsleg/calculations/stats.py`
2. Return DataFrame or add to existing model
3. Integrate in `cli.py` before calling `generate_html()`
4. Update HTML template in `ui/html.py` to display new data

### Modifying Luck Calculation
Edit `calculate_luck_stats()` or `calculate_cumulative_luck_stats()` in `calculations/stats.py`
- Current logic: For each week, simulate team vs all other teams; true win % = simulated wins / total opponents

### Changing Schedule/Deployment
Edit `.github/workflows/deploy.yml` cron expression
- Example: `*/5 18-23 * * 0` = every 5 min on Sunday 1-6pm ET (18:00-23:59 UTC)
- Remember: GitHub Actions uses UTC time exclusively

### Debugging API Issues
1. Check `LeagueClient` logs in Actions output (uses Python logging)
2. Verify league_id in Sleeper app UI
3. Test locally: `fantasy-league` will show stack trace if API fails
4. Use `try/except APIError` to catch connection/timeout issues
