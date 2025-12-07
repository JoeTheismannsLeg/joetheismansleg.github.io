"""Modern HTML generation with template support."""

import logging
from typing import Dict, List, Optional
from datetime import datetime

import pandas as pd
from jinja2 import Template

from .models import Matchup, TeamRecord

logger = logging.getLogger(__name__)

# CSS styling (extracted to constant for easier maintenance)
STYLESHEET = """
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    background: linear-gradient(135deg, #013369 0%, #1a4d8f 100%);
    min-height: 100vh;
    padding: 20px;
}

.container {
    max-width: 1200px;
    margin: 0 auto;
    background: white;
    border-radius: 12px;
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
    padding: 40px;
}

h1 {
    color: #013369;
    margin-bottom: 10px;
    text-align: center;
    font-size: 2.5em;
    background: linear-gradient(135deg, #013369 0%, #d50a0a 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

.season-year {
    text-align: center;
    color: #666;
    font-size: 1.1em;
    margin-bottom: 30px;
    font-weight: 500;
}

.controls {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 15px;
    margin-bottom: 30px;
    flex-wrap: wrap;
}

label {
    font-weight: 600;
    color: #555;
    font-size: 1.1em;
}

select {
    padding: 10px 15px;
    font-size: 1em;
    border: 2px solid #013369;
    border-radius: 8px;
    background: white;
    cursor: pointer;
    transition: all 0.3s ease;
    min-width: 150px;
}

select:hover {
    border-color: #d50a0a;
    box-shadow: 0 4px 12px rgba(213, 10, 10, 0.2);
}

select:focus {
    outline: none;
    border-color: #d50a0a;
    box-shadow: 0 0 0 3px rgba(213, 10, 10, 0.1);
}

table {
    width: 100%;
    border-collapse: collapse;
    margin: 20px 0;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    border-radius: 8px;
    overflow: hidden;
}

thead {
    background: linear-gradient(135deg, #013369 0%, #d50a0a 100%);
    color: white;
}

th {
    padding: 18px;
    text-align: left;
    font-weight: 700;
    font-size: 1.05em;
    letter-spacing: 0.5px;
    word-break: break-word;
}

td {
    padding: 16px 18px;
    border-bottom: 1px solid #e0e0e0;
    font-size: 1em;
    color: #333;
}

tbody tr {
    transition: all 0.2s ease;
}

tbody tr:hover {
    background-color: #f5f5f5;
    transform: scale(1.01);
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

tbody tr:last-child td {
    border-bottom: none;
}

tbody tr:nth-child(odd) {
    background-color: #fafafa;
}

.team-name {
    font-weight: 600;
    color: #013369;
}

.score {
    font-weight: 700;
    font-size: 1.15em;
}

.bye-week {
    color: #999;
    font-style: italic;
}

.winner {
    background-color: #fff3cd;
    font-weight: 700;
    color: #d50a0a;
}

.luck-positive {
    background-color: #d4edda;
    font-weight: 600;
    color: #155724;
}

.luck-negative {
    background-color: #f8d7da;
    font-weight: 600;
    color: #721c24;
}

.luck-neutral {
    background-color: #fff3cd;
    font-weight: 600;
    color: #856404;
}

.trend-up {
    color: #28a745;
    font-weight: 700;
    font-size: 1.3em;
}

.trend-down {
    color: #dc3545;
    font-weight: 700;
    font-size: 1.3em;
}

.trend-stable {
    color: #ffc107;
    font-weight: 700;
    font-size: 1.3em;
}

.info-tabs {
    display: flex;
    gap: 10px;
    margin: 20px 0;
    flex-wrap: wrap;
}

.tab-button {
    padding: 10px 20px;
    border: 2px solid #013369;
    background: white;
    color: #013369;
    cursor: pointer;
    border-radius: 6px;
    font-weight: 600;
    transition: all 0.3s ease;
}

.tab-button.active {
    background: #013369;
    color: white;
}

.tab-button:hover {
    background: #d50a0a;
    border-color: #d50a0a;
    color: white;
}

.tab-content {
    display: none;
}

.tab-content.active {
    display: block;
}

.stats-info {
    background: #f8f9fa;
    border-left: 4px solid #013369;
    padding: 15px;
    margin-bottom: 20px;
    border-radius: 4px;
}

.stats-info h3 {
    color: #013369;
    margin-bottom: 10px;
}

.stats-info p {
    color: #555;
    line-height: 1.6;
    font-size: 0.95em;
}

.footer {
    margin-top: 40px;
    text-align: center;
    color: #888;
    font-size: 0.9em;
    padding-top: 20px;
    border-top: 1px solid #e0e0e0;
}

.scroll-wrapper {
    overflow-x: auto;
    margin: 20px 0;
}

.scroll-wrapper table {
    margin: 0;
}
"""


HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ league_name }} - Matchups</title>
    <style>{{ stylesheet }}</style>
</head>
<body>
    <div class="container">
        <h1>{{ league_name }}</h1>
        <div class="season-year">{{ season }} Season</div>
        
        <div class="controls">
            <label for="weekSelector">Select Week:</label>
            <select id="weekSelector"></select>
        </div>
        
        <div class="info-tabs">
            <button class="tab-button active" onclick="switchTab('matchups')">Matchups</button>
            <button class="tab-button" onclick="switchTab('standings')">Standings</button>
            <button class="tab-button" onclick="switchTab('stats')">Behind the Cue Ball</button>
        </div>
        
        <div id="matchups" class="tab-content active">
            <div id="matchupContainer"></div>
        </div>
        
        <div id="standings" class="tab-content">
            <div id="standingsContainer"></div>
        </div>
        
        <div id="stats" class="tab-content">
            <div class="stats-info">
                <h3>Behind the Cue Ball - Luck Statistics</h3>
                <p><strong>Win %:</strong> Team's actual cumulative win percentage</p>
                <p><strong>True %:</strong> Win percentage if the team played all other teams each week</p>
                <p><strong>Luck:</strong> Difference between actual and true win percentage (positive = lucky, negative = unlucky)</p>
                <p><strong>Delta Luck:</strong> Week-to-week change in luck factor</p>
                <p><strong>Trend:</strong> ↑ improving, ↓ declining, → stable</p>
            </div>
            <div class="scroll-wrapper">
                <div id="statsContainer"></div>
            </div>
        </div>
        
        <div class="footer">Last Updated: {{ timestamp }}</div>
    </div>
    
    <script>
        const weeklyTables = {{ weekly_tables_json }};
        const standingsHtml = `{{ standings_html }}`;
        const statsHtml = `{{ stats_html }}`;
        const activeWeek = {{ active_week }};
        
        const weekSelector = document.getElementById('weekSelector');
        const matchupContainer = document.getElementById('matchupContainer');
        const standingsContainer = document.getElementById('standingsContainer');
        const statsContainer = document.getElementById('statsContainer');
        
        function switchTab(tabName) {
            document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-button').forEach(b => b.classList.remove('active'));
            document.getElementById(tabName).classList.add('active');
            event.target.classList.add('active');
        }
        
        const weeks = Object.keys(weeklyTables).map(w => parseInt(w)).sort((a, b) => a - b);
        weeks.forEach(week => {
            const option = document.createElement('option');
            option.value = week;
            option.textContent = `Week ${week}`;
            if (week === activeWeek) option.selected = true;
            weekSelector.appendChild(option);
        });
        
        function displayWeekMatchups() {
            const selectedWeek = weekSelector.value;
            matchupContainer.innerHTML = weeklyTables[selectedWeek] || '<p>No matchups found.</p>';
        }
        
        weekSelector.addEventListener('change', displayWeekMatchups);
        
        // Initialize displays
        displayWeekMatchups();
        standingsContainer.innerHTML = standingsHtml;
        statsContainer.innerHTML = statsHtml;
    </script>
</body>
</html>
"""


def generate_html(
    matchups: List[Matchup],
    standings: List[TeamRecord],
    league_name: str = "Fantasy League",
    season: int = None,
    luck_stats: Optional[List[Dict]] = None,
) -> str:
    """
    Generate HTML page using modern approach.
    
    Args:
        matchups: List of Matchup objects
        standings: List of TeamRecord objects
        league_name: League name
        season: Season year
        luck_stats: Optional list of luck stat dictionaries from calculate_cumulative_luck_stats
        
    Returns:
        HTML page as string
    """
    if season is None:
        season = datetime.now().year
    
    # Group matchups by week
    matchups_by_week: Dict[int, List[Matchup]] = {}
    for m in matchups:
        if m.week not in matchups_by_week:
            matchups_by_week[m.week] = []
        matchups_by_week[m.week].append(m)
    
    # Generate HTML for each week
    weekly_tables = {}
    for week, week_matchups in sorted(matchups_by_week.items()):
        df = pd.DataFrame([
            {
                'Team 1': m.team_1,
                'Score 1': m.score_1,
                'Team 2': m.team_2,
                'Score 2': m.score_2,
            }
            for m in week_matchups
        ])
        
        if not df.empty:
            html = df.to_html(index=False, classes='matchup-table')
            html = html.replace('<td>', '<td class="cell">')
            html = html.replace('<th>', '<th class="header-cell">')
            weekly_tables[week] = html
    
    # Generate standings HTML
    standings_df = pd.DataFrame([s.to_dict() for s in standings])
    standings_html = ""
    if not standings_df.empty:
        html = standings_df.to_html(index=False, classes='standings-table')
        html = html.replace('<td>', '<td class="cell">')
        html = html.replace('<th>', '<th class="header-cell">')
        standings_html = html
    
    # Generate luck stats HTML
    stats_html = ""
    if luck_stats:
        df = pd.DataFrame(luck_stats)
        
        # Select columns to display
        display_cols = ['Team', 'Week', 'Win %', 'True %', 'Luck', 'Delta Luck', 'Trend']
        if all(col in df.columns for col in display_cols):
            df_display = df[display_cols].copy()
        else:
            df_display = df
        
        # Convert to HTML
        html = df_display.to_html(index=False, classes='stats-table', escape=False)
        
        # Add styling based on luck value
        html = html.replace('<td>', '<td class="cell">')
        html = html.replace('<th>', '<th class="header-cell">')
        
        # Style luck column with color coding
        luck_col_idx = list(display_cols).index('Luck') if 'Luck' in display_cols else -1
        if luck_col_idx >= 0:
            lines = html.split('\n')
            new_lines = []
            in_tbody = False
            for line in lines:
                if '<tbody>' in line:
                    in_tbody = True
                    new_lines.append(line)
                elif '</tbody>' in line:
                    in_tbody = False
                    new_lines.append(line)
                elif in_tbody and '<td class="cell">' in line:
                    # Count td elements to find luck column
                    td_count = len([x for x in new_lines[-10:] if '<tr>' in x or '<td' in x])
                    new_lines.append(line)
                else:
                    new_lines.append(line)
            
            html = '\n'.join(new_lines)
        
        # Style trend column
        html = html.replace('>↑<', ' class="trend-up">↑<')
        html = html.replace('>↓<', ' class="trend-down">↓<')
        html = html.replace('>→<', ' class="trend-stable">→<')
        
        stats_html = html
    
    # Determine active week
    active_week = 1
    for week in sorted(matchups_by_week.keys(), reverse=True):
        week_matches = matchups_by_week[week]
        if any(not m.is_incomplete() and not m.is_bye() for m in week_matches):
            if any(m.score_1 > 0 or m.score_2 > 0 for m in week_matches if not m.is_bye()):
                active_week = week
                break
    
    # Prepare template context
    import json
    template_context = {
        'stylesheet': STYLESHEET,
        'league_name': league_name,
        'season': season,
        'timestamp': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'),
        'weekly_tables_json': json.dumps(weekly_tables),
        'standings_html': standings_html,
        'stats_html': stats_html,
        'active_week': active_week,
    }
    
    # Render template
    template = Template(HTML_TEMPLATE)
    return template.render(**template_context)
