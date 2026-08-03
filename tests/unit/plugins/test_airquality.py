"""Tests for the airquality plugin."""

import json
import pytest
from app.plugins.airquality import (
    process_airquality_json,
    _get_aqi_label,
)


def _make_airquality_response(aqi=2, components=None):
    """Build a minimal OpenWeather Air Pollution API response."""
    if components is None:
        components = {
            "co": 233.4,
            "no": 0.01,
            "no2": 15.6,
            "o3": 118.6,
            "so2": 1.7,
            "pm2_5": 3.8,
            "pm10": 5.2,
            "nh3": 0.4,
        }
    return {
        "coord": {"lon": -122.4194, "lat": 37.7749},
        "list": [
            {
                "main": {"aqi": aqi},
                "components": components,
                "dt": 1624133700,
            }
        ],
    }


class TestAqiLabel:
    def test_aqi_1_good(self):
        desc, emoji = _get_aqi_label(1)
        assert desc == "Good"
        assert emoji == "☑"

    def test_aqi_2_fair(self):
        desc, emoji = _get_aqi_label(2)
        assert desc == "Fair"

    def test_aqi_3_moderate(self):
        desc, emoji = _get_aqi_label(3)
        assert desc == "Moderate"

    def test_aqi_4_poor(self):
        desc, emoji = _get_aqi_label(4)
        assert desc == "Poor"

    def test_aqi_5_very_poor(self):
        desc, emoji = _get_aqi_label(5)
        assert desc == "Very Poor"

    def test_unknown_aqi(self):
        desc, emoji = _get_aqi_label(99)
        assert desc == "Unknown"


class TestProcessAirQualityJson:
    def test_basic_airquality(self):
        response = _make_airquality_response(aqi=2)
        result = process_airquality_json(json.dumps(response), "San Francisco")

        assert "Air Quality for San Francisco" in result
        assert "AQI: 2/5" in result
        assert "Fair" in result

    def test_good_airquality(self):
        response = _make_airquality_response(aqi=1)
        result = process_airquality_json(json.dumps(response), "Denver")

        assert "AQI: 1/5" in result
        assert "Good" in result
        assert "satisfactory" in result.lower()

    def test_poor_airquality(self):
        response = _make_airquality_response(aqi=4)
        result = process_airquality_json(json.dumps(response), "Delhi")

        assert "AQI: 4/5" in result
        assert "Poor" in result
        assert "reduce" in result.lower()

    def test_very_poor_airquality(self):
        response = _make_airquality_response(aqi=5)
        result = process_airquality_json(json.dumps(response), "Beijing")

        assert "AQI: 5/5" in result
        assert "Very Poor" in result
        assert "avoid" in result.lower()

    def test_includes_pollutants(self):
        response = _make_airquality_response(aqi=2)
        result = process_airquality_json(json.dumps(response), "San Francisco")

        assert "Pollutants:" in result
        assert "PM2.5: 3.8" in result
        assert "PM10: 5.2" in result
        assert "O3: 118.6" in result
        assert "NO2: 15.6" in result
        assert "SO2: 1.7" in result
        assert "CO: 233.4" in result

    def test_minimal_components(self):
        components = {"pm2_5": 10.0}
        response = _make_airquality_response(aqi=3, components=components)
        result = process_airquality_json(json.dumps(response), "Test City")

        assert "PM2.5: 10.0" in result
        # Other pollutants not in response shouldn't appear
        assert "NO2" not in result

    def test_empty_response(self):
        response = {"cod": "200", "list": []}
        result = process_airquality_json(json.dumps(response), "Nowhere")
        assert "no air quality data" in result

    def test_invalid_json(self):
        result = process_airquality_json("not json", "Test")
        assert "could not parse air quality data" in result

    def test_health_guidance_shown(self):
        response = _make_airquality_response(aqi=3)
        result = process_airquality_json(json.dumps(response), "Test City")

        assert "Unusually sensitive people" in result

    def test_units_displayed(self):
        response = _make_airquality_response(aqi=2)
        result = process_airquality_json(json.dumps(response), "San Francisco")

        assert "ug/m3" in result  # micrograms per cubic meter
        assert "ppb" in result  # parts per billion for gases
