"""
Bot plugin to summarize a web page using a smaller,
faster model than the default chat model.
"""

import json
import datetime
from urllib.parse import quote_plus

from app.backends.Ircawp_Backend import Ircawp_Backend
from app.media_backends.MediaBackend import MediaBackend
from app.lib.network import fetchHtml
from .__PluginBase import PluginBase


def _geocodeLocation(query: str, api_key: str) -> tuple[str, float, float]:
    """Convert location name to coordinates using OpenWeather Geocoding API.
    Returns (location_name, latitude, longitude)
    """
    # Check if query looks like a US ZIP code (5 digits)
    if query.strip().isdigit() and len(query.strip()) == 5:
        # Use ZIP code endpoint
        url = f"https://api.openweathermap.org/geo/1.0/zip?zip={query.strip()},US&appid={api_key}"
        try:
            response = fetchHtml(url, bypass_cache=True)
            data = json.loads(response)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid API response for ZIP code '{query}': {str(e)}")

        if not data or "lat" not in data:
            raise ValueError(f"ZIP code '{query}' not found")

        location_name = data.get("name", query)
        if "country" in data:
            location_name = f"{location_name}, {data['country']}"

        return location_name, data["lat"], data["lon"]
    else:
        # Use regular location name endpoint
        url = f"https://api.openweathermap.org/geo/1.0/direct?q={quote_plus(query)}&limit=1&appid={api_key}"
        try:
            response = fetchHtml(url, bypass_cache=True)
            data = json.loads(response)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid API response for location '{query}': {str(e)}")

        if not data or len(data) == 0:
            raise ValueError(f"Location '{query}' not found")

        result = data[0]
        location_name = result["name"]
        if "state" in result and result["state"]:
            location_name = f"{location_name}, {result['state']}"
        elif "country" in result:
            location_name = f"{location_name}, {result['country']}"

        return location_name, result["lat"], result["lon"]


def _fahrenheitToCelsius(fahrenheit: float) -> float:
    """Convert Fahrenheit to Celsius."""
    return (fahrenheit - 32) * 5 / 9


def _mphToKph(mph: float) -> float:
    """Convert miles per hour to kilometers per hour."""
    return mph * 1.60934


def _degreesToCompass(degrees: int) -> str:
    """Convert meteorological degrees to 16-point compass direction."""
    directions = [
        "N",
        "NNE",
        "NE",
        "ENE",
        "E",
        "ESE",
        "SE",
        "SSE",
        "S",
        "SSW",
        "SW",
        "WSW",
        "W",
        "WNW",
        "NW",
        "NNW",
    ]
    index = round(degrees / 22.5) % 16
    return directions[index]


def _formatLocalTime(timestamp: int, timezone_offset: int) -> str:
    """Convert Unix UTC timestamp to local formatted time string."""
    local_dt = datetime.datetime.utcfromtimestamp(timestamp + timezone_offset)
    return local_dt.strftime("%Y-%m-%d %I:%M %p")


def _estimateTimeOfDay(timestamp: int, timezone_offset: int) -> str:
    # Convert Unix UTC timestamp to local time using timezone offset
    # 8pm to 4am is night
    # 4am to 12pm is morning
    # 12pm to 4pm is afternoon
    # 4pm to 8pm is evening

    if not timestamp:
        return "daytime"

    local_dt = datetime.datetime.utcfromtimestamp(timestamp + timezone_offset)
    time = local_dt.time()

    if time >= datetime.time(20, 0) or time < datetime.time(4, 0):
        return "night"
    elif time >= datetime.time(4, 0) and time < datetime.time(12, 0):
        return "morning"
    elif time >= datetime.time(12, 0) and time < datetime.time(16, 0):
        return "afternoon"
    elif time >= datetime.time(16, 0) and time < datetime.time(20, 0):
        return "evening"
    else:
        return "daytime"


def _estimateTemperature(temp_f: float) -> str:
    # Takes numeric temperature in Fahrenheit
    # 0F to 32F is cold
    # 32F to 50F is cool
    # 50F to 70F is warm
    # 70F to 90F is hot
    # 90F to 100F is very hot
    # 100F to 120F is extremely hot
    # 120F+ is dangerously hot

    if temp_f is None:
        return "temperature"

    if temp_f < -20:
        return "dangerously cold"
    elif temp_f <= 0:
        return "freezing"
    elif temp_f <= 32:
        return "cold"
    elif temp_f <= 50:
        return "cool"
    elif temp_f <= 70:
        return "warm"
    elif temp_f <= 90:
        return "hot"
    elif temp_f <= 100:
        return "very hot"
    elif temp_f <= 120:
        return "extremely hot"
    else:
        return "dangerously hot"


def _normalizeWeatherType(weather: str) -> str:
    weather = weather.lower()

    if weather == "rain":
        return "rainy"

    return weather


def buildImageGenPrompt(
    where: str, desc: str, temp_f: float, timestamp: int, timezone_offset: int
) -> str:
    location = where.strip()

    kind_of_weather = _normalizeWeatherType(desc.strip())

    temp = _estimateTemperature(temp_f)

    time_of_day = _estimateTimeOfDay(timestamp, timezone_offset)

    return f"professional street-level photo of {location} featuring {temp} {kind_of_weather} weather at {time_of_day}."


def process_weather_json(json_text: str, location_name: str) -> tuple[str, str]:
    """
    Parse OpenWeather Current Weather Data API 2.5 response.
    https://openweathermap.org/current
    """
    try:
        weather_data = json.loads(json_text)

        if "main" not in weather_data:
            return "Error: no current condition data.", ""

        main = weather_data["main"]

        # Temperature (imperial units from API)
        temp_f = main["temp"]
        feels_like_f = main["feels_like"]

        # Convert to Celsius
        temp_c = _fahrenheitToCelsius(temp_f)
        feels_like_c = _fahrenheitToCelsius(feels_like_f)

        temps = f"{temp_f:.0f}F ({temp_c:.0f}C)"

        if (
            abs(temp_f - feels_like_f) > 2
        ):  # Only show "feels like" if difference is noticeable
            temps = f"{temps}, feels like {feels_like_f:.0f}F ({feels_like_c:.0f}C)"

        humidity = main["humidity"]
        desc = weather_data["weather"][0]["description"].title()

        # Wind (imperial units from API)
        wind_mph = weather_data["wind"]["speed"]
        wind_kph = _mphToKph(wind_mph)
        wind_deg = weather_data["wind"].get("deg", 0)
        wind_dir = _degreesToCompass(wind_deg)

        # Time information
        timestamp = weather_data["dt"]
        timezone_offset = weather_data["timezone"]
        observed = _formatLocalTime(timestamp, timezone_offset)

        imagegen_prompt = buildImageGenPrompt(
            location_name,
            desc,
            temp_f,
            timestamp,
            timezone_offset,
        )

        return (
            f"Weather for {location_name}: {desc} at 🌡 {temps}, winds 🌬 {wind_dir} at {wind_mph:.0f}mph ({wind_kph:.0f}kph), 💦 humidity at {humidity}%. (⏰ As of {observed}, local.)",
            imagegen_prompt,
        )

    except (json.decoder.JSONDecodeError, KeyError) as e:
        return f"Error: could not parse weather data - {str(e)}", ""


def doWeather(
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

        disable_imagegen = backend.config.get("weather", {}).get(
            "disable_imagegen", False
        )

        # Step 1: Geocode the location query
        backend.console.log(f"[blue]Geocoding location: {query}")
        location_name, lat, lon = _geocodeLocation(query, api_key)
        backend.console.log(f"[green]Found: {location_name} ({lat}, {lon})")

        # Step 2: Fetch weather data using coordinates (imperial units)
        weather_url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&units=imperial&appid={api_key}"
        backend.console.log(f"[blue]Fetching weather from: {weather_url}")
        content = fetchHtml(weather_url, bypass_cache=True)

        # Debug: Log first 200 chars of response
        backend.console.log(f"[yellow]API Response preview: {content[:200]}")

        processed, prompt = process_weather_json(content, location_name)

        image_path = ""
        skip_imagegen = True

        # Only attempt image generation if a media backend is available
        if media_backend and not disable_imagegen:
            try:
                backend.console.log(
                    f"[blue]Generating weather image with prompt: {prompt}"
                )
                image_path, final_prompt = media_backend.execute(
                    prompt=prompt,
                    config={"aspect": "16:9"},
                    backend=backend,
                )
                skip_imagegen = False
            except Exception as img_e:
                # Log via backend console if available; still return text result
                backend.console.log(f"[yellow]Image generation failed: {img_e}")
                image_path = ""
                skip_imagegen = True

        return processed, image_path, skip_imagegen, {}

    except ValueError as e:
        # Geocoding error (location not found)
        return f"Location error: {str(e)}", "", False, {}
    except Exception as e:
        return (
            f"OpenWeather error: {str(e)}",
            "",
            False,
            {},
        )


plugin = PluginBase(
    name="Weather Plugin",
    description="Get the weather for a location from wttr.in",
    triggers=["weather"],
    system_prompt="Weather for a location from wttr.in",
    emoji_prefix="🌦",
    msg_empty_query="No location provided",
    msg_exception_prefix="WTTR PROBLEMS",
    main=doWeather,
    use_imagegen=False,
)
