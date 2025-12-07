"""Modern HTML generation with template support."""

import logging
from typing import Dict, List, Optional
from datetime import datetime

import pandas as pd
from jinja2 import Template

from ..models import Matchup, TeamRecord

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
    cursor: pointer;
    user-select: none;
    position: relative;
}

th:hover {
    background-color: rgba(255, 255, 255, 0.1);
}

.sort-indicator {
    margin-left: 5px;
    font-size: 0.9em;
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
            <label for="yearSelector">Select Year:</label>
            <select id="yearSelector"></select>
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
        const statsTableData = {{ stats_table_data_json }};
        const allYears = {{ all_years_json }};
        const standingsHtml = `{{ standings_html }}`;
        const activeWeek = {{ active_week }};
        const activeSeason = {{ active_season }};
        
        const yearSelector = document.getElementById('yearSelector');
        const weekSelector = document.getElementById('weekSelector');
        const matchupContainer = document.getElementById('matchupContainer');
        const standingsContainer = document.getElementById('standingsContainer');
        const statsContainer = document.getElementById('statsContainer');
        
        let currentSortColumn = null;
        let currentSortDirection = 'asc';
        
        function switchTab(tabName) {
            document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-button').forEach(b => b.classList.remove('active'));
            document.getElementById(tabName).classList.add('active');
            event.target.classList.add('active');
        }
        
        // Populate year selector
        allYears.forEach(year => {
            const option = document.createElement('option');
            option.value = year;
            option.textContent = `${year} Season`;
            if (year === activeSeason) option.selected = true;
            yearSelector.appendChild(option);
        });
        
        // Populate week selector
        function updateWeekSelector() {
            weekSelector.innerHTML = '';
            const selectedYear = parseInt(yearSelector.value);
            const weeksForYear = Object.keys(statsTableData[selectedYear] || {})
                .map(w => parseInt(w))
                .sort((a, b) => a - b);
            
            weeksForYear.forEach(week => {
                const option = document.createElement('option');
                option.value = week;
                option.textContent = `Week ${week}`;
                if (week === activeWeek && selectedYear === activeSeason) option.selected = true;
                weekSelector.appendChild(option);
            });
            
            displayWeekMatchups();
        }
        
        function displayWeekMatchups() {
            const selectedWeek = weekSelector.value;
            matchupContainer.innerHTML = weeklyTables[selectedWeek] || '<p>No matchups found.</p>';
        }
        
        function displayStats() {
            const selectedYear = parseInt(yearSelector.value);
            const selectedWeek = parseInt(weekSelector.value);
            
            const yearData = statsTableData[selectedYear] || {};
            const weekData = yearData[selectedWeek] || [];
            
            if (weekData.length === 0) {
                statsContainer.innerHTML = '<p>No stats data available for this week.</p>';
                return;
            }
            
            // Create sortable table from raw data
            const table = createSortableTable(weekData);
            statsContainer.innerHTML = table;
            attachTableListeners();
        }
        
        function createSortableTable(data) {
            if (data.length === 0) return '<p>No data available.</p>';
            
            const columns = Object.keys(data[0]);
            let html = '<table class="stats-table"><thead><tr>';
            
            columns.forEach(col => {
                html += `<th class="sortable" data-column="${col}">${col} <span class="sort-indicator"></span></th>`;
            });
            
            html += '</tr></thead><tbody>';
            
            data.forEach(row => {
                html += '<tr>';
                columns.forEach(col => {
                    let cellContent = row[col];
                    let cellClass = 'cell';
                    
                    // Add styling for luck columns
                    if (col === 'Luck') {
                        const val = parseFloat(cellContent);
                        if (val > 0.01) cellClass += ' luck-positive';
                        else if (val < -0.01) cellClass += ' luck-negative';
                        else cellClass += ' luck-neutral';
                    }
                    
                    // Add styling for trend
                    if (col === 'Trend') {
                        if (cellContent === '↑') cellClass += ' trend-up';
                        else if (cellContent === '↓') cellClass += ' trend-down';
                        else if (cellContent === '→') cellClass += ' trend-stable';
                    }
                    
                    html += `<td class="${cellClass}">${cellContent}</td>`;
                });
                html += '</tr>';
            });
            
            html += '</tbody></table>';
            return html;
        }
        
        function attachTableListeners() {
            document.querySelectorAll('th.sortable').forEach(th => {
                th.addEventListener('click', () => sortTable(th));
            });
        }
        
        function sortTable(th) {
            const column = th.dataset.column;
            const selectedYear = parseInt(yearSelector.value);
            const selectedWeek = parseInt(weekSelector.value);
            
            // Toggle sort direction
            if (currentSortColumn === column) {
                currentSortDirection = currentSortDirection === 'asc' ? 'desc' : 'asc';
            } else {
                currentSortColumn = column;
                currentSortDirection = 'asc';
            }
            
            const yearData = statsTableData[selectedYear] || {};
            const weekData = (yearData[selectedWeek] || []).slice();
            
            // Sort data
            weekData.sort((a, b) => {
                let aVal = a[column];
                let bVal = b[column];
                
                // Handle percentage strings (e.g., "88.9%")
                if (String(aVal).includes('%') && String(bVal).includes('%')) {
                    const aNum = parseFloat(aVal.replace('%', ''));
                    const bNum = parseFloat(bVal.replace('%', ''));
                    return currentSortDirection === 'asc' ? aNum - bNum : bNum - aNum;
                }
                
                // Try to parse as number
                const aNum = parseFloat(aVal);
                const bNum = parseFloat(bVal);
                
                if (!isNaN(aNum) && !isNaN(bNum)) {
                    return currentSortDirection === 'asc' ? aNum - bNum : bNum - aNum;
                }
                
                // String comparison
                if (currentSortDirection === 'asc') {
                    return String(aVal).localeCompare(String(bVal));
                } else {
                    return String(bVal).localeCompare(String(aVal));
                }
            });
            
            // Update display
            const table = createSortableTable(weekData);
            statsContainer.innerHTML = table;
            
            // Update sort indicators
            document.querySelectorAll('th.sortable').forEach(header => {
                const indicator = header.querySelector('.sort-indicator');
                if (header.dataset.column === column) {
                    indicator.textContent = currentSortDirection === 'asc' ? '▲' : '▼';
                } else {
                    indicator.textContent = '';
                }
            });
            
            attachTableListeners();
        }
        
        // Event listeners
        yearSelector.addEventListener('change', updateWeekSelector);
        weekSelector.addEventListener('change', () => {
            displayWeekMatchups();
            displayStats();
        });
        
        // Initialize displays
        updateWeekSelector();
        standingsContainer.innerHTML = standingsHtml;
        displayStats();
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
    historical_luck_stats: Optional[Dict[int, List[Dict]]] = None,
) -> str:
    """
    Generate HTML page using modern approach.
    
    Args:
        matchups: List of Matchup objects (current season)
        standings: List of TeamRecord objects (current season)
        league_name: League name
        season: Season year (current season)
        luck_stats: Optional list of luck stat dictionaries for current season
        historical_luck_stats: Optional dict mapping year -> list of luck stats
        
    Returns:
        HTML page as string
    """
    if season is None:
        season = datetime.now().year
    
    # Organize luck stats by year and week
    stats_table_data: Dict[int, Dict[int, List[Dict]]] = {}
    
    # Current season stats
    if luck_stats:
        stats_by_week: Dict[int, List[Dict]] = {}
        for stat in luck_stats:
            week = stat.get('Week', 1)
            if week not in stats_by_week:
                stats_by_week[week] = []
            stats_by_week[week].append(stat)
        stats_table_data[season] = stats_by_week
    
    # Historical stats
    if historical_luck_stats:
        for year, year_stats in historical_luck_stats.items():
            stats_by_week = {}
            for stat in year_stats:
                week = stat.get('Week', 1)
                if week not in stats_by_week:
                    stats_by_week[week] = []
                stats_by_week[week].append(stat)
            stats_table_data[year] = stats_by_week
    
    # Get all available years
    all_years = sorted(stats_table_data.keys(), reverse=True)
    if not all_years:
        all_years = [season]
    
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
    
    # Generate luck stats data (keep as JSON for JavaScript processing)
    stats_html = ""  # No longer pre-rendered, JS handles it
    
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
        'stats_table_data_json': json.dumps(stats_table_data),
        'all_years_json': json.dumps(all_years),
        'active_week': active_week,
        'active_season': season,
    }
    
    # Render template
    template = Template(HTML_TEMPLATE)
    return template.render(**template_context)
