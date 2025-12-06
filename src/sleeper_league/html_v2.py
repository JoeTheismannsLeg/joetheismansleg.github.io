"""Modern HTML generation with template support."""

import logging
from typing import Dict, List
from dataclasses import asdict
from datetime import datetime

import pandas as pd
from jinja2 import Template

from .models import Matchup, TeamRecord, SeasonStats

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
    max-width: 1000px;
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

.footer {
    margin-top: 40px;
    text-align: center;
    color: #888;
    font-size: 0.9em;
    padding-top: 20px;
    border-top: 1px solid #e0e0e0;
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
        </div>
        
        <div id="matchups" class="tab-content active">
            <div id="matchupContainer"></div>
        </div>
        
        <div id="standings" class="tab-content">
            <div id="standingsContainer"></div>
        </div>
        
        <div class="footer">Last Updated: {{ timestamp }}</div>
    </div>
    
    <script>
        const weeklyTables = {{ weekly_tables_json }};
        const standingsHtml = `{{ standings_html }}`;
        const activeWeek = {{ active_week }};
        
        const weekSelector = document.getElementById('weekSelector');
        const matchupContainer = document.getElementById('matchupContainer');
        const standingsContainer = document.getElementById('standingsContainer');
        
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
        document.querySelector('[onclick*="standings"]').addEventListener('click', 
            () => { standingsContainer.innerHTML = standingsHtml; });
        
        displayWeekMatchups();
    </script>
</body>
</html>
"""


def generate_html(
    matchups: List[Matchup],
    standings: List[TeamRecord],
    league_name: str = "Fantasy League",
    season: int = None,
) -> str:
    """
    Generate HTML page using modern approach.
    
    Args:
        matchups: List of Matchup objects
        standings: List of TeamRecord objects
        league_name: League name
        season: Season year
        
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
        'active_week': active_week,
    }
    
    # Render template
    template = Template(HTML_TEMPLATE)
    return template.render(**template_context)
