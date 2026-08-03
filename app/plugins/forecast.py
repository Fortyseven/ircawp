"""
Bot plugin to fetch a 5-day weather forecast using the
OpenWeather 5-Day/3-Hour Forecast API.
"""

import json
import datetime
from urllib.parse import quote_plus

from app.backends.Ircawp_Backend import Ircawp_Backend
from app.media_backends.MediaBackend import MediaBackend
from app.lib.network import fetchHtml
from .__PluginBase import PluginBase
from .weather import (
    _geocodeLocation,
    _fahrenheitToCelsius,
    _mphToKph,
    _degreesToCompass,
)


# Weather condition code to emoji mapping
# Exact codes first, then group-based fallback (2xx, 3xx, 5xx, 6xx, 7xx)
CONDITION_EMOJI_EXACT = {
    800: "☀️",  # Clear sky
    801: "🌤",  # Few clouds
    802: "⛅",  # Scattered clouds
    803: "☁️",  # Broken clouds
    804: "☁️",  # Overcast clouds
}

CONDITION_EMOJI_GROUP = {
    200: "⛈",  # 2xx: Thunderstorm
    300: "🌧",  # 3xx: Drizzle
    500: "🌧",  # 5xx: Rain
    600: "🌨",  # 6xx: Snow
    700: "🌫",  # 7xx: Atmosphere (mist, smoke, haze, etc.)
}


def _get_condition_emoji(weather_id: int) -> str:
    """Map OpenWeather condition code to emoji."""
    if weather_id in CONDITION_EMOJI_EXACT:
        return CONDITION_EMOJI_EXACT[weather_id]
    group = (weather_id // 100) * 100
    return CONDITION_EMOJI_GROUP.get(group, "🌡")


def _format_forecast_time(dt_txt: str) -> str:
    """Parse dt_txt string and return a readable time label."""
    # Format: "2023-06-30 12:00:00"
    dt = datetime.datetime.strptime(dt_txt, "%Y-%m-%d %H:%M:%S")
    hour = dt.hour

    if 5 <= hour < 12:
        return "Morning"
    elif 12 <= hour < 17:
        return "Afternoon"
    elif 17 <= hour < 21:
        return "Evening"
    else:
        return "Night"


def _format_day_date(dt_txt: str) -> str:
    """Parse dt_txt string and return a short day label."""
    dt = datetime.datetime.strptime(dt_txt, "%Y-%m-%d %H:%M:%S")
    today = datetime.datetime.now(datetime.timezone.utc)
    tomorrow = today + datetime.timedelta(days=1)

    if dt.date() == today.date():
        return "Today"
    elif dt.date() == tomorrow.date():
        return "Tomorrow"
    else:
        return dt.strftime("%a %b %d")


def _format_temp(temp_f: float) -> str:
    """Format temperature with both F and C."""
    temp_c = _fahrenheitToCelsius(temp_f)
    return f"{temp_f:.0f}F ({temp_c:.0f}C)"


def _group_by_day(forecast_list: list) -> dict:
    """Group forecast entries by date. Returns {date_str: [entries]}."""
    days = {}
    for entry in forecast_list:
        dt_txt = entry["dt_txt"]
        date_str = dt_txt.split(" ")[0]
        if date_str not in days:
            days[date_str] = []
        days[date_str].append(entry)
    return days


def _pick_period_entry(entries: list, period: str) -> dict | None:
    """Pick the best entry for a given period from a day's entries."""
    period_hours = {
        "Morning": (5, 12),
        "Afternoon": (12, 17),
        "Evening": (17, 21),
        "Night": (21, 5),  # wraps around midnight
    }

    start, end = period_hours[period]
    best = None
    for entry in entries:
        dt = datetime.datetime.strptime(entry["dt_txt"], "%Y-%m-%d %H:%M:%S")
        hour = dt.hour
        if start >= end:  # Night wraps around
            if hour >= start or hour < end:
                best = entry
                break
        else:
            if start <= hour < end:
                best = entry
                break
    return best


def _get_precipitation(entry: dict) -> str | None:
    """Check for rain/snow in a forecast entry and return amount string."""
    rain = entry.get("rain", {})
    snow = entry.get("snow", {})

    rain_3h = rain.get("3h", 0)
    snow_3h = snow.get("3h", 0)

    if rain_3h and snow_3h:
        return f"rain {rain_3h:.1f}mm + snow {snow_3h:.1f}mm"
    elif rain_3h:
        return f"rain {rain_3h:.1f}mm"
    elif snow_3h:
        return f"snow {snow_3h:.1f}mm"
    return None


def process_forecast_json(
    json_text: str, location_name: str, full: bool = False
) -> str:
    """
    Parse OpenWeather 5-Day/3-Hour Forecast API response.
    https://openweathermap.org/forecast5

    Args:
        json_text: Raw JSON response string.
        location_name: Display name for the location.
        full: If True, include per-period breakdown (Morning/Afternoon/Evening/Night).
    """
    try:
        forecast_data = json.loads(json_text)

        if "list" not in forecast_data or len(forecast_data["list"]) == 0:
            return "Error: no forecast data available."

        forecast_list = forecast_data["list"]
        days = _group_by_day(forecast_list)

        # Limit to 5 days max
        day_keys = list(days.keys())[:5]

        lines = [f"Forecast for {location_name}:"]

        for date_str in day_keys:
            entries = days[date_str]
            day_label = _format_day_date(entries[0]["dt_txt"])

            # Calculate daily high/low
            temps = [e["main"]["temp"] for e in entries]
            temp_high = max(temps)
            temp_low = min(temps)

            # Get most common weather condition (pick midday entry as representative)
            midday_entry = _pick_period_entry(entries, "Afternoon")
            if not midday_entry:
                midday_entry = entries[0]
            main_weather = midday_entry["weather"][0]
            emoji = _get_condition_emoji(main_weather["id"])
            desc = main_weather["description"].title()

            # Day header
            lines.append(
                f"{day_label} · {emoji} {desc} · "
                f"High: {_format_temp(temp_high)} · Low: {_format_temp(temp_low)}"
            )

            # Period breakdown (only with --full)
            if not full:
                continue

            periods = ["Morning", "Afternoon", "Evening", "Night"]

            for period in periods:
                entry = _pick_period_entry(entries, period)
                if not entry:
                    continue

                temp = entry["main"]["temp"]
                weather = entry["weather"][0]
                p_emoji = _get_condition_emoji(weather["id"])
                p_desc = weather["description"].title()

                # Add wind if notable
                wind_mph = entry["wind"]["speed"]
                wind_str = ""
                if wind_mph > 10:
                    wind_deg = entry["wind"].get("deg", 0)
                    wind_dir = _degreesToCompass(wind_deg)
                    wind_kph = _mphToKph(wind_mph)
                    wind_str = f" · {wind_dir} {wind_mph:.0f}mph"

                # Add precipitation
                precip = _get_precipitation(entry)
                precip_str = f" · {precip}" if precip else ""

                lines.append(
                    f"  {period}: {p_emoji} {p_desc} · {_format_temp(temp)}{wind_str}{precip_str}"
                )

        return "\n".join(lines)

    except (json.decoder.JSONDecodeError, KeyError) as e:
        return f"Error: could not parse forecast data - {str(e)}"


def _parse_query(query: str) -> tuple[str, bool]:
    """Parse location and flags from query string.

    Returns (location, full_mode).
    Strips --full flag if present.
    """
    full = False
    parts = query.strip().split()

    if "--full" in parts:
        full = True
        parts.remove("--full")

    location = " ".join(parts).strip()
    return location, full


def doForecast(
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

        # Parse query for location and --full flag
        location, full = _parse_query(query)
        if not location:
            return "No location provided", "", True, {}

        # Step 1: Geocode the location query
        backend.console.log(f"[blue]Geocoding location: {location}")
        location_name, lat, lon = _geocodeLocation(location, api_key)
        backend.console.log(f"[green]Found: {location_name} ({lat}, {lon})")

        # Step 2: Fetch forecast data (imperial units, limit to 40 entries = 5 days)
        forecast_url = (
            f"https://api.openweathermap.org/data/2.5/forecast"
            f"?lat={lat}&lon={lon}&units=imperial&cnt=40&appid={api_key}"
        )
        backend.console.log(f"[blue]Fetching forecast from: {forecast_url}")
        content = fetchHtml(forecast_url, bypass_cache=True)

        # Debug: Log first 200 chars of response
        backend.console.log(f"[yellow]API Response preview: {content[:200]}")

        result = process_forecast_json(content, location_name, full=full)

        return result, "", True, {}

    except ValueError as e:
        # Geocoding error (location not found)
        return f"Location error: {str(e)}", "", True, {}
    except Exception as e:
        return (
            f"Forecast error: {str(e)}",
            "",
            True,
            {},
        )


plugin = PluginBase(
    name="Forecast Plugin",
    description="Get a 5-day weather forecast for a location",
    triggers=["forecast"],
    system_prompt="5-day weather forecast for a location",
    emoji_prefix="📅",
    msg_empty_query="No location provided",
    msg_exception_prefix="FORECAST ERROR",
    main=doForecast,
    use_imagegen=False,
)
