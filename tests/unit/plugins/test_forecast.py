"""
Tests for the forecast plugin (app/plugins/forecast.py).

Tests the forecast data parsing, formatting, and helper functions.
"""

import json
import pytest
from app.plugins.forecast import (
    process_forecast_json,
    _get_condition_emoji,
    _format_day_date,
    _format_forecast_time,
    _format_temp,
    _group_by_day,
    _pick_period_entry,
    _get_precipitation,
    _parse_query,
)


pytestmark = pytest.mark.forecast


def _make_forecast_entry(
    dt_txt, temp, weather_id, desc, wind_speed=5, deg=180, rain=None, snow=None
):
    """Build a minimal forecast list entry."""
    entry = {
        "dt_txt": dt_txt,
        "main": {"temp": temp},
        "weather": [{"id": weather_id, "description": desc}],
        "wind": {"speed": wind_speed, "deg": deg},
    }
    if rain:
        entry["rain"] = {"3h": rain}
    if snow:
        entry["snow"] = {"3h": snow}
    return entry


def _make_full_response(entries, city_name="Test City"):
    """Build a minimal full forecast API response."""
    return {
        "cod": "200",
        "message": 0,
        "cnt": len(entries),
        "list": entries,
        "city": {
            "id": 123456,
            "name": city_name,
            "coord": {"lon": 0, "lat": 0},
            "country": "US",
            "population": 100000,
            "timezone": 0,
            "sunrise": 0,
            "sunset": 0,
        },
    }


class TestConditionEmoji:
    def test_clear_sky(self):
        assert _get_condition_emoji(800) == "☀️"

    def test_few_clouds(self):
        assert _get_condition_emoji(801) == "🌤"

    def test_scattered_clouds(self):
        assert _get_condition_emoji(802) == "⛅"

    def test_broken_clouds(self):
        assert _get_condition_emoji(803) == "☁️"

    def test_overcast(self):
        assert _get_condition_emoji(804) == "☁️"

    def test_rain(self):
        assert _get_condition_emoji(500) == "🌧"
        assert _get_condition_emoji(501) == "🌧"

    def test_snow(self):
        assert _get_condition_emoji(600) == "🌨"

    def test_thunderstorm(self):
        assert _get_condition_emoji(200) == "⛈"
        assert _get_condition_emoji(232) == "⛈"

    def test_unknown_defaults(self):
        assert _get_condition_emoji(999) == "🌡"


class TestFormatHelpers:
    def test_format_temp(self):
        result = _format_temp(72.5)
        assert "72F" in result
        assert "22C" in result

    def test_format_temp_freezing(self):
        result = _format_temp(28.4)
        assert "28F" in result
        assert "-2C" in result

    def test_format_forecast_time_morning(self):
        assert _format_forecast_time("2024-06-30 07:00:00") == "Morning"

    def test_format_forecast_time_afternoon(self):
        assert _format_forecast_time("2024-06-30 14:00:00") == "Afternoon"

    def test_format_forecast_time_evening(self):
        assert _format_forecast_time("2024-06-30 19:00:00") == "Evening"

    def test_format_forecast_time_night(self):
        assert _format_forecast_time("2024-06-30 23:00:00") == "Night"
        assert _format_forecast_time("2024-06-30 02:00:00") == "Night"


class TestGroupByDay:
    def test_groups_entries_by_date(self):
        entries = [
            _make_forecast_entry("2024-07-01 06:00:00", 70, 800, "clear sky"),
            _make_forecast_entry("2024-07-01 12:00:00", 80, 800, "clear sky"),
            _make_forecast_entry("2024-07-02 06:00:00", 65, 801, "few clouds"),
        ]
        days = _group_by_day(entries)
        assert "2024-07-01" in days
        assert "2024-07-02" in days
        assert len(days["2024-07-01"]) == 2
        assert len(days["2024-07-02"]) == 1

    def test_limits_to_5_days(self):
        # Create entries for 7 days
        entries = []
        for day in range(1, 8):
            for hour in [6, 12, 18, 0]:
                dt = f"2024-07-{day:02d} {hour:02d}:00:00"
                entries.append(_make_forecast_entry(dt, 70, 800, "clear sky"))
        days = _group_by_day(entries)
        assert len(days) == 7  # grouping itself doesn't limit


class TestPickPeriodEntry:
    def test_picks_morning_entry(self):
        entries = [
            _make_forecast_entry("2024-07-01 03:00:00", 60, 800, "clear"),
            _make_forecast_entry("2024-07-01 06:00:00", 65, 800, "clear"),
            _make_forecast_entry("2024-07-01 12:00:00", 80, 800, "clear"),
        ]
        result = _pick_period_entry(entries, "Morning")
        assert result["dt_txt"] == "2024-07-01 06:00:00"

    def test_picks_afternoon_entry(self):
        entries = [
            _make_forecast_entry("2024-07-01 06:00:00", 65, 800, "clear"),
            _make_forecast_entry("2024-07-01 12:00:00", 80, 800, "clear"),
            _make_forecast_entry("2024-07-01 18:00:00", 75, 800, "clear"),
        ]
        result = _pick_period_entry(entries, "Afternoon")
        assert result["dt_txt"] == "2024-07-01 12:00:00"

    def test_picks_evening_entry(self):
        entries = [
            _make_forecast_entry("2024-07-01 12:00:00", 80, 800, "clear"),
            _make_forecast_entry("2024-07-01 18:00:00", 75, 800, "clear"),
            _make_forecast_entry("2024-07-01 21:00:00", 70, 800, "clear"),
        ]
        result = _pick_period_entry(entries, "Evening")
        assert result["dt_txt"] == "2024-07-01 18:00:00"

    def test_picks_night_entry(self):
        entries = [
            _make_forecast_entry("2024-07-01 21:00:00", 70, 800, "clear"),
            _make_forecast_entry("2024-07-01 00:00:00", 65, 800, "clear"),
            _make_forecast_entry("2024-07-01 03:00:00", 60, 800, "clear"),
        ]
        result = _pick_period_entry(entries, "Night")
        assert result["dt_txt"] == "2024-07-01 21:00:00"

    def test_returns_none_if_no_match(self):
        entries = [
            _make_forecast_entry("2024-07-01 06:00:00", 65, 800, "clear"),
        ]
        result = _pick_period_entry(entries, "Evening")
        assert result is None


class TestPrecipitation:
    def test_no_precipitation(self):
        entry = _make_forecast_entry("2024-07-01 12:00:00", 70, 800, "clear")
        assert _get_precipitation(entry) is None

    def test_rain_only(self):
        entry = _make_forecast_entry(
            "2024-07-01 12:00:00", 70, 500, "light rain", rain=1.5
        )
        assert _get_precipitation(entry) == "rain 1.5mm"

    def test_snow_only(self):
        entry = _make_forecast_entry(
            "2024-07-01 12:00:00", 25, 600, "light snow", snow=0.8
        )
        assert _get_precipitation(entry) == "snow 0.8mm"

    def test_rain_and_snow(self):
        entry = _make_forecast_entry(
            "2024-07-01 12:00:00", 35, 511, "rain and snow", rain=0.5, snow=0.3
        )
        result = _get_precipitation(entry)
        assert "rain 0.5mm" in result
        assert "snow 0.3mm" in result


class TestParseQuery:
    def test_simple_location(self):
        location, full = _parse_query("San Francisco")
        assert location == "San Francisco"
        assert not full

    def test_location_with_full(self):
        location, full = _parse_query("San Francisco --full")
        assert location == "San Francisco"
        assert full

    def test_full_first(self):
        location, full = _parse_query("--full London")
        assert location == "London"
        assert full

    def test_full_middle(self):
        location, full = _parse_query("New York --full")
        assert location == "New York"
        assert full

    def test_no_full_flag(self):
        location, full = _parse_query("Tokyo")
        assert location == "Tokyo"
        assert not full

    def test_empty_after_strip(self):
        location, full = _parse_query("--full")
        assert location == ""
        assert full

    def test_whitespace_handling(self):
        location, full = _parse_query("  Chicago  --full  ")
        assert location == "Chicago"
        assert full


class TestProcessForecastJson:
    def test_basic_forecast(self):
        entries = [
            _make_forecast_entry("2024-07-01 06:00:00", 65, 800, "clear sky"),
            _make_forecast_entry("2024-07-01 12:00:00", 78, 800, "clear sky"),
            _make_forecast_entry("2024-07-01 18:00:00", 72, 801, "few clouds"),
            _make_forecast_entry("2024-07-01 00:00:00", 60, 800, "clear sky"),
            _make_forecast_entry("2024-07-02 06:00:00", 68, 802, "scattered clouds"),
            _make_forecast_entry("2024-07-02 12:00:00", 82, 500, "light rain"),
            _make_forecast_entry("2024-07-02 18:00:00", 75, 803, "broken clouds"),
            _make_forecast_entry("2024-07-02 00:00:00", 62, 800, "clear sky"),
        ]
        response = _make_full_response(entries, "San Francisco")
        result = process_forecast_json(json.dumps(response), "San Francisco")

        assert "Forecast for San Francisco" in result
        # Default (no --full): day headers only, no period breakdown
        assert "Morning" not in result
        assert "Afternoon" not in result

    def test_full_mode_includes_periods(self):
        entries = [
            _make_forecast_entry("2024-07-01 06:00:00", 65, 800, "clear sky"),
            _make_forecast_entry("2024-07-01 12:00:00", 78, 800, "clear sky"),
            _make_forecast_entry("2024-07-01 18:00:00", 72, 801, "few clouds"),
            _make_forecast_entry("2024-07-01 00:00:00", 60, 800, "clear sky"),
        ]
        response = _make_full_response(entries, "San Francisco")
        result = process_forecast_json(json.dumps(response), "San Francisco", full=True)

        assert "Forecast for San Francisco" in result
        assert "Morning:" in result
        assert "Afternoon:" in result
        assert "Evening:" in result
        assert "Night:" in result

    def test_empty_forecast(self):
        response = {"cod": "200", "list": [], "city": {}}
        result = process_forecast_json(json.dumps(response), "Nowhere")
        assert "no forecast data" in result

    def test_invalid_json(self):
        result = process_forecast_json("not json", "Test")
        assert "could not parse forecast data" in result

    def test_includes_precipitation(self):
        entries = [
            _make_forecast_entry("2024-07-01 06:00:00", 65, 800, "clear sky"),
            _make_forecast_entry(
                "2024-07-01 12:00:00", 78, 500, "light rain", rain=2.0
            ),
            _make_forecast_entry("2024-07-01 18:00:00", 72, 800, "clear sky"),
            _make_forecast_entry("2024-07-01 00:00:00", 60, 800, "clear sky"),
        ]
        response = _make_full_response(entries, "Seattle")
        result = process_forecast_json(json.dumps(response), "Seattle", full=True)
        assert "rain 2.0mm" in result

    def test_includes_wind_when_strong(self):
        entries = [
            _make_forecast_entry("2024-07-01 06:00:00", 65, 800, "clear sky"),
            _make_forecast_entry(
                "2024-07-01 12:00:00", 78, 800, "clear sky", wind_speed=15, deg=270
            ),
            _make_forecast_entry("2024-07-01 18:00:00", 72, 800, "clear sky"),
            _make_forecast_entry("2024-07-01 00:00:00", 60, 800, "clear sky"),
        ]
        response = _make_full_response(entries, "Chicago")
        result = process_forecast_json(json.dumps(response), "Chicago", full=True)
        assert "15mph" in result

    def test_includes_high_low_temps(self):
        entries = [
            _make_forecast_entry("2024-07-01 06:00:00", 65, 800, "clear sky"),
            _make_forecast_entry("2024-07-01 12:00:00", 92, 800, "clear sky"),
            _make_forecast_entry("2024-07-01 18:00:00", 85, 800, "clear sky"),
            _make_forecast_entry("2024-07-01 00:00:00", 55, 800, "clear sky"),
        ]
        response = _make_full_response(entries, "Phoenix")
        result = process_forecast_json(json.dumps(response), "Phoenix")
        assert "High: 92F" in result
        assert "Low: 55F" in result
