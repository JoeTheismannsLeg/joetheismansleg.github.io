"""Command-line interface for fantasy league data fetcher."""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Tuple as _Tuple

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
        postseason_matchups = load_postseason_matchups(current_season, client=client, regular_matchups=matchups)
        logger.info(f"Loaded {len(postseason_matchups)} postseason matchups")

        # Merge postseason matchups with regular matchups
        all_matchups = matchups + postseason_matchups

        # Generate HTML with historical data + additional_tables (now with extra analytics)
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

        # Helper to convert objects to plain dicts for JSON/JS consumption
        def _rowify(obj):
            if obj is None:
                return {}
            if hasattr(obj, "to_dict"):
                try:
                    return obj.to_dict()
                except Exception:
                    pass
            if isinstance(obj, dict):
                return obj
            try:
                return dict(obj)
            except Exception:
                try:
                    # fallback: use __dict__
                    return obj.__dict__
                except Exception:
                    return {"value": str(obj)}

        # Build additional_tables with real data for Data Tables tab
        additional_tables: Dict[int, Dict[str, Dict]] = {}
        season_tables: Dict[str, Dict] = {}

        # 1) Standings (season-level)
        try:
            season_tables["Standings"] = {"_season": [_rowify(s) for s in standings] if standings else []}
        except Exception:
            season_tables["Standings"] = {"_season": []}

        # 2) Cumulative Luck (season-level)
        try:
            cumulative = calculate_cumulative_luck_stats(all_matchups)
            season_tables["Cumulative Luck"] = {"_season": cumulative}
        except Exception:
            season_tables["Cumulative Luck"] = {"_season": []}

        # 3) Weekly Luck (week-keyed)
        try:
            weekly_by_week: Dict[str, List[Dict]] = {}
            for ls in luck_stats or []:
                row = _rowify(ls)
                wk = str(row.get("Week", row.get("week", 1)))
                weekly_by_week.setdefault(wk, []).append(row)
            season_tables["Weekly Luck"] = {**weekly_by_week, "_season": []}
        except Exception:
            season_tables["Weekly Luck"] = {"_season": []}

        # Prepare data structures for requested new tables:
        # - Head-to-Head matrix (team x team with W-L)
        # - Top scoring placements counts (team-level: times in top3, top5; opponent top3/top5)
        # - Average weekly scoring rank of opponents (team-level)

        # Gather teams from standings (preferred) or from matchups
        try:
            teams = [row.get("team") if isinstance(row, dict) else getattr(row, "team", None) for row in standings]
            teams = [t for t in teams if t]
            if not teams:
                # Fall back to teams from matchups
                teams_set = set()
                for m in all_matchups:
                    if not m.is_bye() and not m.is_incomplete():
                        teams_set.add(m.team_1)
                        teams_set.add(m.team_2)
                teams = sorted(list(teams_set))
        except Exception:
            teams = []
            teams_set = set()
            for m in all_matchups:
                if not m.is_bye() and not m.is_incomplete():
                    teams_set.add(m.team_1)
                    teams_set.add(m.team_2)
            teams = sorted(list(teams_set))

        # Build week -> team -> score mapping and week matchups list
        week_team_scores: Dict[int, Dict[str, float]] = {}
        week_matchups: Dict[int, List[Matchup]] = {}
        for m in all_matchups:
            if m.is_bye() or m.is_incomplete():
                continue
            wk = int(m.week)
            week_team_scores.setdefault(wk, {})
            week_matchups.setdefault(wk, [])
            # if duplicate entries for the same team/week exist, later ones will overwrite
            week_team_scores[wk][m.team_1] = m.score_1
            week_team_scores[wk][m.team_2] = m.score_2
            week_matchups[wk].append(m)

        # Compute head-to-head win counts: wins[(winner, loser)] = count
        wins: Dict[_Tuple[str, str], int] = {}
        for m in all_matchups:
            if m.is_bye() or m.is_incomplete():
                continue
            w = m.winner()
            if w is None or w == 0:
                continue
            if w == 1:
                winner = m.team_1
                loser = m.team_2
            else:
                winner = m.team_2
                loser = m.team_1
            wins[(winner, loser)] = wins.get((winner, loser), 0) + 1

        # Head-to-head matrix as list of rows: {'Team': T, 'Opp A': 'W-L', ...}
        head_to_head_rows: List[Dict[str, object]] = []
        for team in teams:
            row = {"Team": team}
            for opp in teams:
                if team == opp:
                    row[opp] = "-"
                    continue
                w = wins.get((team, opp), 0)
                l = wins.get((opp, team), 0)
                row[opp] = f"{w}-{l}"
            head_to_head_rows.append(row)
        season_tables["Head-to-Head Matrix"] = {"_season": head_to_head_rows}

        # Build ranking per week: team -> week -> rank (1 is highest scorer)
        team_week_rank: Dict[str, Dict[int, int]] = {t: {} for t in teams}
        for wk, scores in week_team_scores.items():
            # sort teams by score desc; produce rank mapping
            sorted_pairs = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
            # dense rank assignment: same score => same rank
            distinct_rank = 1
            last_score = None
            score_to_rank = {}
            for t, sc in sorted_pairs:
                if sc != last_score:
                    score_to_rank[sc] = distinct_rank
                    last_score = sc
                    distinct_rank += 1
                team_week_rank.setdefault(t, {})[wk] = score_to_rank[sc]

        # For each matchup, record opponent mapping per team per week
        opponent_by_team_week: Dict[str, Dict[int, str]] = {t: {} for t in teams}
        for wk, mlist in week_matchups.items():
            for m in mlist:
                # ensure both teams present
                opponent_by_team_week.setdefault(m.team_1, {})[wk] = m.team_2
                opponent_by_team_week.setdefault(m.team_2, {})[wk] = m.team_1

        # Top scoring placement counts and opponent top placements
        top_counts_rows: List[Dict[str, object]] = []
        for team in teams:
            # Collect weeks team has score
            weeks_played = sorted(team_week_rank.get(team, {}).keys())
            top3 = 0
            top5 = 0
            opp_top3 = 0
            opp_top5 = 0
            opp_ranks = []
            for wk in weeks_played:
                rank = team_week_rank.get(team, {}).get(wk)
                if rank is not None:
                    if rank <= 3:
                        top3 += 1
                    if rank <= 5:
                        top5 += 1
                # opponent checks
                opp = opponent_by_team_week.get(team, {}).get(wk)
                if opp:
                    opp_rank = team_week_rank.get(opp, {}).get(wk)
                    if opp_rank is not None:
                        if opp_rank <= 3:
                            opp_top3 += 1
                        if opp_rank <= 5:
                            opp_top5 += 1
                        opp_ranks.append(opp_rank)
            avg_opp_rank = round((sum(opp_ranks) / len(opp_ranks)), 2) if opp_ranks else None
            top_counts_rows.append(
                {
                    "Team": team,
                    "Top 3 Count": top3,
                    "Top 5 Count": top5,
                    "Opponent Top 3 Count": opp_top3,
                    "Opponent Top 5 Count": opp_top5,
                }
            )
        season_tables["Top Scoring Placements"] = {"_season": top_counts_rows}

        # Average weekly scoring rank of opponents table
        avg_opp_rows: List[Dict[str, object]] = []
        for team in teams:
            opp_ranks = []
            weeks_played = sorted(team_week_rank.get(team, {}).keys())
            for wk in weeks_played:
                opp = opponent_by_team_week.get(team, {}).get(wk)
                if opp:
                    opp_rank = team_week_rank.get(opp, {}).get(wk)
                    if opp_rank is not None:
                        opp_ranks.append(opp_rank)
            avg_rank = round(sum(opp_ranks) / len(opp_ranks), 2) if opp_ranks else None
            avg_opp_rows.append({"Team": team, "Average Opponent Scoring Rank": avg_rank})

        season_tables["Average Opponent Scoring Rank"] = {"_season": avg_opp_rows}

        # Attach season_tables to additional_tables for current season
        additional_tables[current_season] = season_tables

        # Historical seasons: keep previous behavior (attempt to add similar tables if data available)
        for year, mups in (historical_matchups_only or {}).items():
            try:
                year_int = int(year)
            except Exception:
                continue
            year_tables: Dict[str, Dict] = {}
            # Standings
            if historical_standings_only.get(year_int):
                year_tables["Standings"] = {"_season": [_rowify(s) for s in historical_standings_only[year_int]]}
            # Cumulative Luck
            try:
                year_tables["Cumulative Luck"] = {"_season": calculate_cumulative_luck_stats(mups)}
            except Exception:
                year_tables.setdefault("Cumulative Luck", {"_season": []})
            # Weekly Luck from historical_luck_stats if present
            hist_weekly = {}
            if historical_luck_stats_only.get(year_int):
                for ls in historical_luck_stats_only[year_int]:
                    row = _rowify(ls)
                    wk = str(row.get("Week", row.get("week", 1)))
                    hist_weekly.setdefault(wk, []).append(row)
                year_tables["Weekly Luck"] = {**hist_weekly, "_season": []}
            else:
                year_tables.setdefault("Weekly Luck", {"_season": []})
            additional_tables[year_int] = year_tables

        # Now render the page and include the additional_tables
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
            additional_tables=additional_tables,  # <- pass in real data tables
        )

        # Write output
        output_file = Path("index.html")
        output_file.write_text(html_content)
        logger.info(f"Generated HTML report: {output_file}")
        logger.info(f"Report includes {len(historical_luck_stats)} seasons of data (additional_tables keys: {list(additional_tables.keys())})")

        return 0

    except Exception as e:
        logger.exception(f"Error generating report: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
