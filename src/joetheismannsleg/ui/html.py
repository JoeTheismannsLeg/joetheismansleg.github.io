"""Modern HTML generation with template support."""

import logging
import re
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd
from jinja2 import Template

from ..models import Matchup, TeamRecord

logger = logging.getLogger(__name__)


def add_data_labels_to_table(table_html: str) -> str:
    """
    Add data-label attributes to table cells for mobile responsiveness.
    
    This allows the CSS ::before pseudo-element to display column headers
    on mobile devices using the data-label attribute.
    
    Args:
        table_html: HTML string containing a table element
        
    Returns:
        Modified HTML string with data-label attributes added to td elements
    """
    # Extract column headers from the table
    header_match = re.search(r'<thead>.*?<tr[^>]*>(.*?)</tr>.*?</thead>', table_html, re.DOTALL)
    if not header_match:
        return table_html
    
    headers_html = header_match.group(1)
    # Extract all header text from th elements
    headers = re.findall(r'<th[^>]*>([^<]*)</th>', headers_html)
    
    if not headers:
        return table_html
    
    # Find the tbody and process rows
    tbody_match = re.search(r'<tbody>(.*?)</tbody>', table_html, re.DOTALL)
    if not tbody_match:
        return table_html
    
    tbody_html = tbody_match.group(1)
    
    # Process each row in tbody
    rows = re.findall(r'<tr[^>]*>(.*?)</tr>', tbody_html, re.DOTALL)
    modified_tbody = tbody_html
    
    for row_content in rows:
        # Find all cells in this row
        cells = re.findall(r'<td[^>]*>.*?</td>', row_content, re.DOTALL)
        
        if not cells:
            continue
        
        # Add data-labels to each cell
        modified_row = row_content
        for cell_idx, cell in enumerate(cells):
            if cell_idx < len(headers) and 'data-label=' not in cell:
                label = headers[cell_idx].strip()
                new_cell = re.sub(
                    r'<td([^>]*)>',
                    lambda m: f'<td{m.group(1)} data-label="{label}">',
                    cell,
                    count=1
                )
                modified_row = modified_row.replace(cell, new_cell, 1)
        
        # Replace the row in tbody
        modified_tbody = modified_tbody.replace(row_content, modified_row, 1)
    
    # Replace tbody in the original HTML
    result = table_html.replace(tbody_match.group(0), f'<tbody>{modified_tbody}</tbody>', 1)
    
    return result


def generate_matchup_cards(matchups: List[Matchup], week: int) -> str:
    """
    Generate mobile-friendly matchup cards for a list of matchups.
    
    Each card displays:
    - Header: Week number or matchup name
    - Two columns: Team 1 / Team 2
    - Two columns: Score 1 / Score 2
    
    Args:
        matchups: List of Matchup objects
        week: Week number for header
        
    Returns:
        HTML string containing matchup cards
    """
    if not matchups:
        return ""
    
    cards_html = ""
    
    for matchup in matchups:
        # Determine header: use matchup name if available (postseason), otherwise use week
        header = matchup.name if matchup.name else f"Week {week}"
        
        # Build card HTML
        card_html = f'''<div class="matchup-card">
    <div class="matchup-card-header">{header}</div>
    <div class="matchup-card-body">
        <div class="matchup-card-row">
            <div class="matchup-card-team">
                <div class="matchup-card-team-name">{matchup.team_1}</div>
            </div>
            <div class="matchup-card-team">
                <div class="matchup-card-team-name">{matchup.team_2}</div>
            </div>
        </div>
        <div class="matchup-card-row">
            <div class="matchup-card-score">{matchup.score_1:.2f}</div>
            <div class="matchup-card-score">{matchup.score_2:.2f}</div>
        </div>
    </div>
</div>'''
        cards_html += card_html
    
    return cards_html

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

h3 {
    color: #d50a0a;
    font-size: 1.3em;
    font-weight: 600;
    margin-top: 30px;
    margin-bottom: 15px;
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

/* Matchup card styling for mobile */
.matchup-card {
    display: none;
    border: 1px solid #ddd;
    border-radius: 8px;
    background: white;
    margin-bottom: 15px;
    overflow: hidden;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.matchup-card-header {
    background: linear-gradient(135deg, #013369 0%, #1a4d8f 100%);
    color: white;
    padding: 12px 15px;
    font-weight: 600;
    font-size: 0.95em;
}

.matchup-card-body {
    padding: 15px;
}

.matchup-card-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 15px;
    margin-bottom: 10px;
}

.matchup-card-row:last-child {
    margin-bottom: 0;
}

.matchup-card-team {
    text-align: left;
}

.matchup-card-team-name {
    font-weight: 600;
    color: #013369;
    margin-bottom: 5px;
    word-break: break-word;
}

.matchup-card-score {
    text-align: right;
    font-weight: 700;
    color: #d50a0a;
    font-size: 1.1em;
}

/* Mobile-first responsive design */
@media (max-width: 768px) {
    body {
        padding: 10px;
    }

    .container {
        padding: 20px;
        border-radius: 8px;
    }

    h1 {
        font-size: 1.8em;
        margin-bottom: 5px;
    }

    h3 {
        font-size: 1.1em;
        margin-top: 20px;
        margin-bottom: 10px;
    }

    .season-year {
        font-size: 0.95em;
        margin-bottom: 20px;
    }

    .controls {
        flex-direction: column;
        gap: 10px;
    }

    label {
        font-size: 0.95em;
        width: 100%;
        text-align: left;
    }

    select {
        width: 100%;
        min-width: unset;
        padding: 8px 12px;
        font-size: 0.95em;
    }

    table {
        margin: 15px 0;
        font-size: 0.85em;
    }

    thead {
        display: none;
    }

    tr {
        display: block;
        margin-bottom: 15px;
        border: 1px solid #ddd;
        border-radius: 6px;
        overflow: hidden;
        background: white;
    }

    tbody tr:nth-child(odd) {
        background-color: white;
    }

    tbody tr:hover {
        transform: none;
        background-color: #f5f5f5;
    }

    td {
        display: block;
        padding: 10px 12px;
        border-bottom: 1px solid #e0e0e0;
        border-left: 3px solid #013369;
        text-align: right;
    }

    td:last-child {
        border-bottom: none;
    }

    td:before {
        content: attr(data-label);
        float: left;
        font-weight: 700;
        color: #013369;
        text-transform: uppercase;
        font-size: 0.75em;
        letter-spacing: 0.5px;
    }

    /* Show matchup cards on mobile */
    .matchup-card {
        display: block;
    }

    /* Hide tables on mobile when cards are shown */
    table {
        display: none;
    }

    .team-name {
        display: inline;
    }

    .bye-week {
        font-size: 0.9em;
    }

    .info-tabs {
        gap: 5px;
    }

    .tab-button {
        padding: 8px 12px;
        font-size: 0.85em;
        border-width: 1px;
    }

    .stats-info {
        padding: 12px;
        border-left-width: 3px;
    }

    .stats-info p {
        font-size: 0.9em;
    }

    .footer {
        margin-top: 20px;
        font-size: 0.85em;
        padding-top: 15px;
    }
}

@media (max-width: 480px) {
    body {
        padding: 8px;
    }

    .container {
        padding: 15px;
    }

    h1 {
        font-size: 1.4em;
    }

    h3 {
        font-size: 1em;
        margin-top: 15px;
    }

    .controls {
        gap: 8px;
    }

    label {
        font-size: 0.9em;
    }

    select {
        padding: 6px 10px;
        font-size: 0.9em;
    }

    table {
        font-size: 0.8em;
    }

    td {
        padding: 8px 10px;
    }

    .score {
        font-size: 1em;
    }

    .tab-button {
        padding: 6px 10px;
        font-size: 0.8em;
    }

    .tab-button:hover {
        transform: none;
    }
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
        
        <div class="footer">
            <div>Last Updated: {{ timestamp }}</div>
            {% if git_branch and git_commit != 'n/a' %}
            <div>
                Branch: <a href="https://github.com/JoeTheismannsLeg/joetheismansleg.github.io/tree/{{ git_branch }}" target="_blank" rel="noopener noreferrer">{{ git_branch }}</a>
                | Commit: <a href="https://github.com/JoeTheismannsLeg/joetheismansleg.github.io/commit/{{ git_commit_full }}" target="_blank" rel="noopener noreferrer">{{ git_commit }}</a>
            </div>
            {% endif %}
        </div>
    </div>
    
    <script>
        const weeklyTables = {{ weekly_tables_json }};
        const standingsByYear = {{ standings_by_year_json }};
        const statsTableData = {{ stats_table_data_json }};
        const allYears = {{ all_years_json }};
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
            const selectedYearStr = String(selectedYear);
            const weeksForYear = Object.keys(weeklyTables[selectedYearStr] || {})
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
            displayStandings();
        }
        
        function displayWeekMatchups() {
            const selectedYear = parseInt(yearSelector.value);
            const selectedYearStr = String(selectedYear);
            const selectedWeek = parseInt(weekSelector.value);
            const weekStr = String(selectedWeek);
            const yearTables = weeklyTables[selectedYearStr] || {};
            matchupContainer.innerHTML = yearTables[weekStr] || '<p>No matchups found.</p>';
        }
        
        function displayStandings() {
            const selectedYear = parseInt(yearSelector.value);
            const selectedYearStr = String(selectedYear);
            standingsContainer.innerHTML = standingsByYear[selectedYearStr] || '<p>No standings data available.</p>';
        }
        
        function displayStats() {
            const selectedYear = parseInt(yearSelector.value);
            const selectedYearStr = String(selectedYear);
            const selectedWeek = parseInt(weekSelector.value);
            const weekStr = String(selectedWeek);
            
            const yearData = statsTableData[selectedYearStr] || {};
            const weekData = yearData[weekStr] || [];
            
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
            displayStandings();
            displayStats();
        });
        
        // Initialize displays
        updateWeekSelector();
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
    historical_matchups: Optional[Dict[int, List[Matchup]]] = None,
    historical_standings: Optional[Dict[int, List[TeamRecord]]] = None,
    historical_luck_stats: Optional[Dict[int, List[Dict]]] = None,
    git_branch: Optional[str] = None,
    git_commit: Optional[str] = None,
    git_commit_full: Optional[str] = None,
) -> str:
    """
    Generate HTML page using modern approach.

    Args:
        matchups: List of Matchup objects (current season)
        standings: List of TeamRecord objects (current season)
        league_name: League name
        season: Season year (current season)
        luck_stats: Optional list of luck stat dictionaries for current season
        historical_matchups: Optional dict mapping year -> list of matchups for that year
        historical_standings: Optional dict mapping year -> list of standings for that year
        historical_luck_stats: Optional dict mapping year -> list of luck stats for that year
        git_branch: Optional current git branch name
        git_commit: Optional short git commit hash (for display)
        git_commit_full: Optional full git commit hash (for GitHub links)

    Returns:
        HTML page as string
    """
    if season is None:
        season = datetime.now().year

    # Ensure season is an integer
    if isinstance(season, str):
        season = int(season)

    # Organize luck stats by year and week
    stats_table_data: Dict[int, Dict[int, List[Dict]]] = {}

    # Current season stats
    if luck_stats:
        stats_by_week: Dict[int, List[Dict]] = {}
        for stat in luck_stats:
            week = stat.get("Week", 1)
            if week not in stats_by_week:
                stats_by_week[week] = []
            stats_by_week[week].append(stat)
        stats_table_data[season] = stats_by_week

    # Historical stats
    if historical_luck_stats:
        for year, year_stats in historical_luck_stats.items():
            year_int = int(year) if isinstance(year, str) else year
            stats_by_week = {}
            for stat in year_stats:
                week = stat.get("Week", 1)
                if week not in stats_by_week:
                    stats_by_week[week] = []
                stats_by_week[week].append(stat)
            stats_table_data[year_int] = stats_by_week

    # Get all available years and ensure they're all integers
    all_years = sorted([int(year) for year in stats_table_data.keys()], reverse=True)
    if not all_years:
        all_years = [season]

    # Organize matchups by year and week
    matchups_by_year_week: Dict[int, Dict[int, List[Matchup]]] = {}

    # Current season matchups
    for m in matchups:
        if season not in matchups_by_year_week:
            matchups_by_year_week[season] = {}
        if m.week not in matchups_by_year_week[season]:
            matchups_by_year_week[season][m.week] = []
        matchups_by_year_week[season][m.week].append(m)

    # Historical matchups
    if historical_matchups:
        for year, year_matchups in historical_matchups.items():
            year_int = int(year) if isinstance(year, str) else year
            if year_int not in matchups_by_year_week:
                matchups_by_year_week[year_int] = {}
            for m in year_matchups:
                if m.week not in matchups_by_year_week[year_int]:
                    matchups_by_year_week[year_int][m.week] = []
                matchups_by_year_week[year_int][m.week].append(m)

    # Generate HTML for each week of each year
    weekly_tables: Dict[int, Dict[int, str]] = {}  # year -> week -> html
    for year in all_years:
        weekly_tables[year] = {}
        year_matchups = matchups_by_year_week.get(year, {})
        for week in sorted(year_matchups.keys()):
            week_matchups = year_matchups[week]
            
            # Separate regular and postseason matchups
            regular_matchups = [m for m in week_matchups if not m.is_postseason()]
            postseason_matchups = [m for m in week_matchups if m.is_postseason()]
            
            # Generate regular matchups table
            html_parts = []
            if regular_matchups:
                df = pd.DataFrame(
                    [
                        {
                            "Team 1": m.team_1,
                            "Score 1": m.score_1,
                            "Team 2": m.team_2,
                            "Score 2": m.score_2,
                        }
                        for m in regular_matchups
                    ]
                )

                if not df.empty:
                    # Add Sleeper matchups title
                    html = "<h3 style='color: #013369; margin-bottom: 15px;'>Sleeper Matchups</h3>"
                    table_html = df.to_html(index=False, classes="matchup-table")
                    table_html = table_html.replace("<td>", '<td class="cell">')
                    table_html = table_html.replace("<th>", '<th class="header-cell">')
                    table_html = add_data_labels_to_table(table_html)
                    html += table_html
                    
                    # Add matchup cards for mobile
                    html += generate_matchup_cards(regular_matchups, week)
                    
                    html_parts.append(html)
            
            # Generate postseason matchups table if present
            if postseason_matchups:
                df = pd.DataFrame(
                    [
                        {
                            "Name": m.name,
                            "Team 1": m.team_1,
                            "Score 1": m.score_1,
                            "Team 2": m.team_2,
                            "Score 2": m.score_2,
                        }
                        for m in postseason_matchups
                    ]
                )

                if not df.empty:
                    # Add JTL postseason title
                    html = "<h3 style='color: #d50a0a; margin-top: 30px; margin-bottom: 15px;'>JTL Matchups</h3>"
                    table_html = df.to_html(index=False, classes="matchup-table")
                    table_html = table_html.replace("<td>", '<td class="cell">')
                    table_html = table_html.replace("<th>", '<th class="header-cell">')
                    table_html = add_data_labels_to_table(table_html)
                    html += table_html
                    
                    # Add matchup cards for mobile
                    html += generate_matchup_cards(postseason_matchups, week)
                    
                    html_parts.append(html)
            
            # Combine all HTML for this week
            if html_parts:
                weekly_tables[year][week] = "".join(html_parts)

    # Organize standings by year
    standings_by_year: Dict[int, str] = {}

    # Current season standings
    standings_df = pd.DataFrame([s.to_dict() for s in standings])
    if not standings_df.empty:
        html = standings_df.to_html(index=False, classes="standings-table")
        html = html.replace("<td>", '<td class="cell">')
        html = html.replace("<th>", '<th class="header-cell">')
        html = add_data_labels_to_table(html)
        standings_by_year[season] = html

    # Historical standings
    if historical_standings:
        for year, year_standings in historical_standings.items():
            year_int = int(year) if isinstance(year, str) else year
            standings_df = pd.DataFrame([s.to_dict() for s in year_standings])
            if not standings_df.empty:
                html = standings_df.to_html(index=False, classes="standings-table")
                html = html.replace("<td>", '<td class="cell">')
                html = html.replace("<th>", '<th class="header-cell">')
                html = add_data_labels_to_table(html)
                standings_by_year[year_int] = html

    # Generate luck stats data (keep as JSON for JavaScript processing)
    stats_html = ""  # No longer pre-rendered, JS handles it

    # Determine active week from current season matchups
    matchups_by_week: Dict[int, List[Matchup]] = {}
    for m in matchups:
        if m.week not in matchups_by_week:
            matchups_by_week[m.week] = []
        matchups_by_week[m.week].append(m)

    active_week = 1
    for week in sorted(matchups_by_week.keys(), reverse=True):
        week_matches = matchups_by_week[week]
        if any(not m.is_incomplete() and not m.is_bye() for m in week_matches):
            # Check if week has scores OR has custom JTL matchups (which should display even with zero scores)
            has_scores = any(m.score_1 > 0 or m.score_2 > 0 for m in week_matches if not m.is_bye())
            has_jtl_matchups = any(m.is_postseason() for m in week_matches)
            if has_scores or has_jtl_matchups:
                active_week = week
                break

    # Prepare template context
    import json

    template_context = {
        "stylesheet": STYLESHEET,
        "league_name": league_name,
        "season": season,
        "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        "git_branch": git_branch,
        "git_commit": git_commit,
        "git_commit_full": git_commit_full,
        "weekly_tables_json": json.dumps(weekly_tables),
        "standings_by_year_json": json.dumps(standings_by_year),
        "stats_html": stats_html,
        "stats_table_data_json": json.dumps(stats_table_data),
        "all_years_json": json.dumps(all_years),
        "active_week": active_week,
        "active_season": season,
    }

    # Render template
    template = Template(HTML_TEMPLATE)
    return template.render(**template_context)
