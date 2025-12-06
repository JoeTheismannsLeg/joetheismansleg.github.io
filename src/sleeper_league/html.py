"""HTML generation utilities for displaying matchups and standings."""

import json
import pandas as pd
from datetime import datetime


def generate_matchup_html(
    matchups_df: pd.DataFrame,
    standings_df: pd.DataFrame,
    league_name: str = "Fantasy League",
    season: int = None
) -> str:
    """
    Generate a complete HTML page with matchups and standings.
    
    Args:
        matchups_df: DataFrame with columns: Week, Team 1, Score 1, Team 2, Score 2
        standings_df: DataFrame with standings (Team, W, L, W%, PF, PA)
        league_name: Name of the league
        season: Season year
    
    Returns:
        Complete HTML page as string
    """
    if season is None:
        season = datetime.now().year
    
    # Generate matchup tables by week
    weekly_tables = {}
    if not matchups_df.empty:
        for week, week_df in matchups_df.groupby('Week'):
            week_df_display = week_df.copy()
            if 'Week' in week_df_display.columns:
                week_df_display = week_df_display.drop(columns=['Week'])
            if 'Matchup ID' in week_df_display.columns:
                week_df_display = week_df_display.drop(columns=['Matchup ID'])
            
            # Generate HTML table
            html_table = week_df_display.to_html(index=False, classes='matchup-table')
            html_table = html_table.replace('<td>', '<td class="cell">')
            html_table = html_table.replace('<th>', '<th class="header-cell">')
            
            # Add styling
            html_table = html_table.replace('<th class="header-cell">Team 1</th>', 
                                           '<th class="header-cell team-name">Team 1</th>')
            html_table = html_table.replace('<th class="header-cell">Team 2</th>', 
                                           '<th class="header-cell team-name">Team 2</th>')
            html_table = html_table.replace('<th class="header-cell">Score 1</th>', 
                                           '<th class="header-cell score">Score 1</th>')
            html_table = html_table.replace('<th class="header-cell">Score 2</th>', 
                                           '<th class="header-cell score">Score 2</th>')
            
            # Add bye week styling
            html_table = html_table.replace('>BYE<', ' class="bye-week">BYE<')
            html_table = html_table.replace('>UNPLAYED/INCOMPLETE<', ' class="bye-week">UNPLAYED/INCOMPLETE<')
            html_table = html_table.replace('>N/A<', ' class="bye-week">N/A<')
            
            weekly_tables[int(week)] = html_table
    
    # Generate standings table
    standings_html = ""
    if not standings_df.empty:
        standings_table = standings_df.to_html(index=False, classes='standings-table')
        standings_table = standings_table.replace('<td>', '<td class="cell">')
        standings_table = standings_table.replace('<th>', '<th class="header-cell">')
        standings_html = f'<h3 class="standings-title">{season} Season Standings</h3>{standings_table}'
    else:
        standings_html = '<p>No standings data available yet.</p>'
    
    # Determine active week
    active_week = 1
    if not matchups_df.empty:
        all_weeks = sorted(matchups_df['Week'].unique())
        for week in reversed(all_weeks):
            week_data = matchups_df[matchups_df['Week'] == week]
            has_real_matchups = not (week_data['Team 2'] == 'UNPLAYED/INCOMPLETE').all()
            if has_real_matchups:
                scores1 = pd.to_numeric(week_data['Score 1'], errors='coerce')
                scores2 = pd.to_numeric(week_data['Score 2'], errors='coerce')
                has_scores = (scores1 > 0).any() or (scores2 > 0).any()
                if has_scores:
                    active_week = int(week)
                    break
    
    # Generate HTML
    current_utc_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
    
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{league_name} - Matchups</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #013369 0%, #1a4d8f 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1000px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            padding: 40px;
        }}
        
        h1 {{
            color: #013369;
            margin-bottom: 10px;
            text-align: center;
            font-size: 2.5em;
            background: linear-gradient(135deg, #013369 0%, #d50a0a 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}
        
        .season-year {{
            text-align: center;
            color: #666;
            font-size: 1.1em;
            margin-bottom: 30px;
            font-weight: 500;
        }}
        
        .controls {{
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 15px;
            margin-bottom: 30px;
            flex-wrap: wrap;
        }}
        
        label {{
            font-weight: 600;
            color: #555;
            font-size: 1.1em;
        }}
        
        select {{
            padding: 10px 15px;
            font-size: 1em;
            border: 2px solid #013369;
            border-radius: 8px;
            background: white;
            cursor: pointer;
            transition: all 0.3s ease;
            min-width: 150px;
        }}
        
        select:hover {{
            border-color: #d50a0a;
            box-shadow: 0 4px 12px rgba(213, 10, 10, 0.2);
        }}
        
        select:focus {{
            outline: none;
            border-color: #d50a0a;
            box-shadow: 0 0 0 3px rgba(213, 10, 10, 0.1);
        }}
        
        #matchupContainer {{
            margin-top: 30px;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 0;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            border-radius: 8px;
            overflow: hidden;
        }}
        
        thead {{
            background: linear-gradient(135deg, #013369 0%, #d50a0a 100%);
            color: white;
        }}
        
        th {{
            padding: 18px;
            text-align: left;
            font-weight: 700;
            font-size: 1.05em;
            letter-spacing: 0.5px;
        }}
        
        td {{
            padding: 16px 18px;
            border-bottom: 1px solid #e0e0e0;
            font-size: 1em;
            color: #333;
        }}
        
        tbody tr {{
            transition: all 0.2s ease;
        }}
        
        tbody tr:hover {{
            background-color: #f5f5f5;
            transform: scale(1.01);
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        }}
        
        tbody tr:last-child td {{
            border-bottom: none;
        }}
        
        tbody tr:nth-child(odd) {{
            background-color: #fafafa;
        }}
        
        .team-name {{
            font-weight: 600;
            color: #013369;
        }}
        
        .team-name a {{
            color: #013369;
            text-decoration: none;
            border-bottom: 2px solid #d50a0a;
            transition: all 0.2s ease;
            cursor: pointer;
        }}
        
        .team-name a:hover {{
            color: #d50a0a;
            border-bottom-color: #013369;
        }}
        
        .score {{
            font-weight: 700;
            font-size: 1.15em;
        }}
        
        .bye-week {{
            color: #999;
            font-style: italic;
        }}
        
        .winner {{
            background-color: #fff3cd;
            font-weight: 700;
            color: #d50a0a;
        }}
        
        .winner-score {{
            background-color: #fff3cd;
            font-weight: 700;
            color: #d50a0a;
            font-size: 1.1em;
        }}
        
        .standings-title {{
            color: #013369;
            font-size: 1.5em;
            font-weight: 700;
            margin: 30px 0 15px 0;
            padding-bottom: 10px;
            border-bottom: 2px solid #d50a0a;
        }}
        
        .info-tabs {{
            display: flex;
            gap: 10px;
            margin: 20px 0;
            flex-wrap: wrap;
        }}
        
        .tab-button {{
            padding: 10px 20px;
            border: 2px solid #013369;
            background: white;
            color: #013369;
            cursor: pointer;
            border-radius: 6px;
            font-weight: 600;
            transition: all 0.3s ease;
        }}
        
        .tab-button.active {{
            background: #013369;
            color: white;
        }}
        
        .tab-button:hover {{
            background: #d50a0a;
            border-color: #d50a0a;
            color: white;
        }}
        
        .tab-content {{
            display: none;
        }}
        
        .tab-content.active {{
            display: block;
        }}
        
        .footer {{
            margin-top: 40px;
            text-align: center;
            color: #888;
            font-size: 0.9em;
            padding-top: 20px;
            border-top: 1px solid #e0e0e0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{league_name}</h1>
        <div class="season-year">{season} Season</div>
        
        <div class="controls">
            <label for="weekSelector">Select Week:</label>
            <select id="weekSelector"></select>
        </div>
        
        <!-- Tab buttons for switching views -->
        <div class="info-tabs">
            <button class="tab-button active" onclick="switchTab('matchups')">Matchups</button>
            <button class="tab-button" onclick="switchTab('standings')">Standings</button>
        </div>
        
        <!-- Matchups tab -->
        <div id="matchups" class="tab-content active">
            <div id="matchupContainer"></div>
        </div>
        
        <!-- Standings tab -->
        <div id="standings" class="tab-content">
            <div id="standingsContainer"></div>
        </div>
        
        <div class="footer">Last Updated: {current_utc_time}</div>
    </div>
</body>
</html>

<script>
    const weeklyTables = {json.dumps(weekly_tables)};
    const standingsHtml = `{standings_html}`;
    const activeWeek = {active_week};
    
    const weekSelector = document.getElementById('weekSelector');
    const matchupContainer = document.getElementById('matchupContainer');
    const standingsContainer = document.getElementById('standingsContainer');
    
    // Tab switching function
    function switchTab(tabName) {{
        // Hide all tabs
        const tabs = document.querySelectorAll('.tab-content');
        tabs.forEach(tab => tab.classList.remove('active'));
        
        // Remove active class from all buttons
        const buttons = document.querySelectorAll('.tab-button');
        buttons.forEach(btn => btn.classList.remove('active'));
        
        // Show selected tab
        document.getElementById(tabName).classList.add('active');
        
        // Highlight clicked button
        event.target.classList.add('active');
        
        // Update standings if that tab is clicked
        if (tabName === 'standings') {{
            displayStandings();
        }}
    }}
    
    // Populate week dropdown
    const weeks = Object.keys(weeklyTables).map(w => parseInt(w)).sort((a, b) => a - b);
    for (const week of weeks) {{
        const option = document.createElement('option');
        option.value = week;
        option.textContent = `Week ${{week}}`;
        if (week === activeWeek) {{
            option.selected = true;
        }}
        weekSelector.appendChild(option);
    }}
    
    // Display selected week's matchups
    function displayWeekMatchups() {{
        const selectedWeek = weekSelector.value;
        if (weeklyTables[selectedWeek]) {{
            matchupContainer.innerHTML = weeklyTables[selectedWeek];
        }} else {{
            matchupContainer.innerHTML = `<p>No matchups found for Week ${{selectedWeek}}.</p>`;
        }}
    }}
    
    // Display standings
    function displayStandings() {{
        standingsContainer.innerHTML = standingsHtml;
    }}
    
    // Event listener for week selection
    weekSelector.addEventListener('change', displayWeekMatchups);
    
    // Initialize on page load
    displayWeekMatchups();
</script>
"""
    
    return html_content
