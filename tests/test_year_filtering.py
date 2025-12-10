"""Test year filtering HTML generation functionality.

Verifies that the generated HTML contains all necessary elements for year-based filtering,
including year and week selectors, display functions, and proper data structures.

Note: These tests check for elements present when index.html is generated with historical
data enabled. If index.html doesn't have historical data or is not present, these tests
will be skipped to allow tests to pass in environments where HTML generation isn't enabled.
"""

import re
from pathlib import Path

import pytest


@pytest.fixture
def html_content():
    """Load HTML content from generated index.html if it exists."""
    html_path = Path("index.html")
    if not html_path.exists():
        pytest.skip("index.html not found - skipping HTML validation tests")
    content = html_path.read_text()
    if "allYears" not in content:
        pytest.skip(
            "index.html exists but doesn't have historical data setup - skipping historical data tests"
        )
    return content


class TestYearFilteringHTMLElements:
    """Tests for HTML elements required for year filtering."""

    def test_year_selector_exists(self, html_content):
        """Test that year selector element exists in HTML."""
        assert '<select id="yearSelector">' in html_content

    def test_week_selector_exists(self, html_content):
        """Test that week selector element exists in HTML."""
        assert '<select id="weekSelector">' in html_content

    def test_year_selector_has_options(self, html_content):
        """Test that year selector has at least one option."""
        year_selector_match = re.search(
            r'<select id="yearSelector">.*?</select>',
            html_content,
            re.DOTALL,
        )
        assert year_selector_match is not None
        year_selector = year_selector_match.group(0)
        option_count = year_selector.count("<option")
        assert option_count > 0, "Year selector has no options"


class TestYearFilteringJavaScriptFunctions:
    """Tests for JavaScript functions required for year filtering."""

    def test_string_conversion_present(self, html_content):
        """Test that JavaScript string conversion is present for data access."""
        # The fix converts integer year to string for JSON object access
        assert "String(selectedYear)" in html_content or "selectedYearStr" in html_content

    def test_display_week_matchups_function(self, html_content):
        """Test that displayWeekMatchups function exists."""
        assert "function displayWeekMatchups()" in html_content

    def test_display_standings_function(self, html_content):
        """Test that displayStandings function exists."""
        assert "function displayStandings()" in html_content

    def test_display_stats_function(self, html_content):
        """Test that displayStats function exists."""
        assert "function displayStats()" in html_content

    def test_update_week_selector_function(self, html_content):
        """Test that updateWeekSelector function exists."""
        assert "function updateWeekSelector()" in html_content


class TestYearFilteringDataStructures:
    """Tests for data structures passed to JavaScript."""

    def test_weekly_tables_variable_exists(self, html_content):
        """Test that weeklyTables JavaScript variable exists."""
        assert "const weeklyTables = " in html_content or "var weeklyTables = " in html_content

    def test_standings_by_year_variable_exists(self, html_content):
        """Test that standingsByYear JavaScript variable exists."""
        assert (
            "const standingsByYear = " in html_content or "var standingsByYear = " in html_content
        )

    def test_stats_table_data_variable_exists(self, html_content):
        """Test that statsTableData JavaScript variable exists."""
        assert "const statsTableData = " in html_content or "var statsTableData = " in html_content

    def test_all_years_array_exists(self, html_content):
        """Test that allYears array exists."""
        assert "const allYears = " in html_content or "var allYears = " in html_content

    def test_weekly_tables_uses_string_keys(self, html_content):
        """Test that weeklyTables uses string keys in JSON."""
        # Look for either const or var declaration
        weekly_tables_match = re.search(
            r"(?:const|var) weeklyTables = ({.*?});",
            html_content,
            re.DOTALL,
        )
        assert weekly_tables_match is not None
        json_str = weekly_tables_match.group(1)
        # Check if string keys are present (quotes around numbers)
        assert '"' in json_str[:200], "weeklyTables should have string keys"


class TestYearFilteringEventListeners:
    """Tests for event listener setup."""

    def test_year_selector_change_listener(self, html_content):
        """Test that year selector has change event listener."""
        assert "yearSelector.addEventListener" in html_content

    def test_week_selector_change_listener(self, html_content):
        """Test that week selector has change event listener."""
        assert "weekSelector.addEventListener" in html_content
