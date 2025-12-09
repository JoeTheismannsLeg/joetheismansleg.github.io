"""Test JSON serialization for year filtering functionality.

Verifies that the JSON serialization creates string keys that JavaScript can access,
and that the type conversion pattern works correctly.
"""

import json


def test_json_serialization_integer_to_string_conversion():
    """Test that Python dicts with integer keys serialize to JSON with string keys."""
    # Simulate the Python data structure (year is int key)
    weekly_tables = {
        2025: {1: "<table>...</table>", 2: "<table>...</table>"},
        2024: {1: "<table>...</table>", 2: "<table>...</table>"},
        2023: {1: "<table>...</table>"},
    }

    # Serialize to JSON
    serialized = json.dumps(weekly_tables)
    parsed = json.loads(serialized)

    # Verify keys are strings
    assert isinstance(list(parsed.keys())[0], str)
    assert "2025" in parsed
    assert "2024" in parsed
    assert "2023" in parsed


def test_json_serialization_nested_access():
    """Test that nested data structures can be accessed after JSON serialization."""
    weekly_tables = {
        2025: {1: "Week 1 data", 2: "Week 2 data"},
        2024: {1: "Week 1 data"},
    }

    serialized = json.dumps(weekly_tables)
    parsed = json.loads(serialized)

    # Test nested access with string keys
    assert parsed["2025"]["1"] == "Week 1 data"
    assert parsed["2025"]["2"] == "Week 2 data"
    assert parsed["2024"]["1"] == "Week 1 data"


def test_javascript_string_conversion_pattern():
    """Test the JavaScript string conversion pattern for data access."""
    standings_by_year = {
        2025: "<table>standings 2025</table>",
        2024: "<table>standings 2024</table>",
        2023: "<table>standings 2023</table>",
    }

    serialized = json.dumps(standings_by_year)
    parsed = json.loads(serialized)

    # Simulate JavaScript: parseInt then String conversion
    selected_year = 2025
    selected_year_str = str(selected_year)  # String() in JavaScript

    # Access data with string key
    result = parsed[selected_year_str]
    assert result == "<table>standings 2025</table>"


def test_all_years_array_access():
    """Test that years array can be used to populate dropdowns."""
    all_years = [2025, 2024, 2023, 2022, 2021, 2020, 2019]
    weekly_tables = {
        2025: {1: "data"},
        2024: {1: "data"},
        2023: {1: "data"},
        2022: {1: "data"},
        2021: {1: "data"},
        2020: {1: "data"},
        2019: {1: "data"},
    }

    serialized = json.dumps(weekly_tables)
    parsed = json.loads(serialized)

    # Verify each year in array can access the data
    for year in all_years:
        year_str = str(year)
        assert year_str in parsed, f"Year {year} missing from data"
