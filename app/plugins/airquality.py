"""
Bot plugin to report air quality for a given location using the
OpenWeather Air Pollution API.
"""

import json
from app.backends.Ircawp_Backend import Ircawp_Backend
from app.media_backends.MediaBackend import MediaBackend
from app.lib.network import fetchHtml
from .__PluginBase import PluginBase
from .weather import _geocodeLocation


# AQI level descriptions and emoji (single codepoints only)
AQI_LEVELS = {
    1: ("Good", "☑"),
    2: ("Fair", "🌤"),
    3: ("Moderate", "⚠"),
    4: ("Poor", "😳"),
    5: ("Very Poor", "😷"),
}

# Pollutant display names and units (ASCII only)
POLLUTANTS = [
    ("pm2_5", "PM2.5", "ug/m3"),
    ("pm10", "PM10", "ug/m3"),
    ("o3", "O3", "ppb"),
    ("no2", "NO2", "ppb"),
    ("so2", "SO2", "ppb"),
    ("co", "CO", "ppb"),
]

# Health guidance per AQI level
HEALTH_GUIDANCE = {
    1: "Air quality is satisfactory. Little or no risk.",
    2: "Acceptable for most people. Unusually sensitive people should consider limiting prolonged outdoor exertion.",
    3: "Unusually sensitive people should consider reducing prolonged or heavy outdoor exertion.",
    4: "Everyone should reduce prolonged or heavy outdoor exertion. Sensitive groups should avoid outdoor activity.",
    5: "Everyone should avoid outdoor activity. Sensitive groups should remain indoors.",
}


def _get_aqi_label(aqi: int) -> tuple[str, str]:
    """Get description and emoji for AQI level."""
    return AQI_LEVELS.get(aqi, ("Unknown", "?"))


def process_airquality_json(json_text: str, location_name: str) -> str:
    """
    Parse OpenWeather Air Pollution API response.
    https://openweathermap.org/api/air-pollution
    """
    try:
        data = json.loads(json_text)

        if "list" not in data or len(data["list"]) == 0:
            return "Error: no air quality data available."

        entry = data["list"][0]
        aqi = entry["main"]["aqi"]
        components = entry.get("components", {})

        desc, emoji = _get_aqi_label(aqi)

        lines = [
            f"Air Quality for {location_name}:",
            f"\n{emoji} AQI: {aqi}/5 ({desc})",
        ]

        # Pollutant breakdown
        pollutant_lines = []
        for key, name, unit in POLLUTANTS:
            value = components.get(key)
            if value is not None:
                pollutant_lines.append(f"  {name}: {value:.1f} {unit}")

        if pollutant_lines:
            lines.append("\nPollutants:")
            lines.extend(pollutant_lines)

        # Health guidance
        guidance = HEALTH_GUIDANCE.get(aqi)
        if guidance:
            lines.append(f"\n{guidance}")

        return "\n".join(lines)

    except (json.decoder.JSONDecodeError, KeyError) as e:
        return f"Error: could not parse air quality data - {str(e)}"


def doAirQuality(
    query: str,
    media: list,
    backend: Ircawp_Backend,
    media_backend: MediaBackend = None,
) -> tuple[str, str, bool, dict]:
    try:
        # Get API key from config
        api_key = backend.config.get("weather", {}).get("api_key")
        if not api_key:
            return (
                "Weather API key not configured. Add 'weather.api_key' to config.yml",
                "",
                True,
                {},
            )

        # Step 1: Geocode the location query
        backend.console.log(f"[blue]Geocoding location: {query}")
        location_name, lat, lon = _geocodeLocation(query, api_key)
        backend.console.log(f"[green]Found: {location_name} ({lat}, {lon})")

        # Step 2: Fetch air quality data
        airquality_url = (
            f"https://api.openweathermap.org/data/2.5/air_pollution"
            f"?lat={lat}&lon={lon}&appid={api_key}"
        )
        backend.console.log(f"[blue]Fetching air quality from: {airquality_url}")
        content = fetchHtml(airquality_url, bypass_cache=True)

        # Debug: Log first 200 chars of response
        backend.console.log(f"[yellow]API Response preview: {content[:200]}")

        result = process_airquality_json(content, location_name)

        return result, "", True, {}

    except ValueError as e:
        # Geocoding error (location not found)
        return f"Location error: {str(e)}", "", True, {}
    except Exception as e:
        return (
            f"Air quality error: {str(e)}",
            "",
            True,
            {},
        )


plugin = PluginBase(
    name="Air Quality Plugin",
    description="Get air quality for a location",
    triggers=["airquality"],
    system_prompt="Air quality for a location",
    emoji_prefix="🌬",
    msg_empty_query="No location provided",
    msg_exception_prefix="AIR QUALITY ERROR",
    main=doAirQuality,
    use_imagegen=False,
)
