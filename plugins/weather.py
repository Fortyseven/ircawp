"""
Bot plugin to summarize a web page using a smaller,
faster model than the default chat model.
"""

import json
import requests
import datetime
from urllib.parse import quote_plus

from backends.BaseBackend import BaseBackend
from plugins.__AskBase import AskBase


def _estimateTimeOfDay(observed: str) -> str:
    # 'observed' requires '10:00 AM' format
    # 8pm to 4am is night
    # 4am to 12pm is morning
    # 12pm to 4pm is afternoon
    # 4pm to 8pm is evening

    if not observed:
        return "daytime"

    time = datetime.datetime.strptime(observed, "%I:%M %p").time()

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


def _estimateTemperature(temp: str) -> str:
    # 'temp' requires '10F (10C)' format
    # 0F to 32F is cold
    # 32F to 50F is cool
    # 50F to 70F is warm
    # 70F to 90F is hot
    # 90F to 100F is very hot
    # 100F to 120F is extremely hot
    # 120F+ is dangerously hot

    if not temp:
        return "temperature"

    temp_f = int(temp.split(" ")[0][:-1])
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
    where, desc, temps, wind_dir, wind_mph, wind_kph, humidity, observed
) -> str:
    location = where.strip()

    kind_of_weather = _normalizeWeatherType(desc.strip())

    temp = temps.strip()
    temp = _estimateTemperature(temp)

    # NOTE: observed is NOT the current time, meaning it might show night
    # time even if it's currently daytime; I can't help this without doing
    # my own time zone lookups, etc. Nothing in wttr.in's JSON response
    # gives me the current time at the locale. If you want this, it will be
    # much more work. Probably. I didn't look into it.

    time_of_day = " ".join(observed.split(" ")[1:])
    time_of_day = _estimateTimeOfDay(time_of_day)

    return f"professional photo of {location} featuring {temp} {kind_of_weather} weather at {time_of_day}"


def process_weather_json(json_text: str) -> tuple[str, str]:
    """
    https://wttr.in/:help
    """
    # decode
    try:
        weather_data = json.loads(json_text)

        if not weather_data["current_condition"]:
            return "Error: no current condition data.", ""

        current = weather_data["current_condition"][0]
        feels_like_f = current["FeelsLikeF"]
        feels_like_c = current["FeelsLikeC"]
        temp_f = current["temp_F"]
        temp_c = current["temp_C"]

        temps = f"{temp_f}F ({temp_c}C)"

        if temp_f != feels_like_f:
            temps = f"{temps}, feels like {feels_like_f}F ({feels_like_c}C)"

        humidity = current["humidity"]
        desc = current["weatherDesc"][0]["value"]

        wind_mph = current["windspeedMiles"]
        wind_kph = current["windspeedKmph"]
        wind_dir = current["winddir16Point"]

        observed = current["localObsDateTime"]

        if (
            not weather_data.get("nearest_area", None)
            or len(weather_data["nearest_area"]) < 1
        ):
            where = "Unknown...?"
        else:
            where = weather_data["nearest_area"][0]["areaName"][0]["value"]
            where2 = weather_data["nearest_area"][0]["region"][0]["value"]

            where = f"{where}, {where2}"

        imagegen_prompt = buildImageGenPrompt(
            where,
            desc,
            temps,
            wind_dir,
            wind_mph,
            wind_kph,
            humidity,
            observed,
        )

        return (
            f"Weather for {where}: {desc} at 🌡 {temps}, winds 🌬 {wind_dir} at {wind_mph}mph ({wind_kph}kph), 💦 humidity at {humidity}%. (⏰ As of {observed}, local.)",
            imagegen_prompt,
        )

    except json.decoder.JSONDecodeError:
        return "Error: could not decode JSON.", ""


def doWeather(query: str, backend: BaseBackend) -> tuple[str, str | dict]:
    try:
        # with open("w.json", "r") as f:
        #     return process_weather_json(f.read())

        url_query = f"https://wttr.in/{quote_plus(query)}?format=j1"
        response = requests.get(url_query, timeout=12, allow_redirects=True)

        if response.status_code >= 400:
            return (
                f"Error: code ({response.status_code}) for ({url_query})",
                "",
            )

        return process_weather_json(response.text)
    except requests.exceptions.Timeout:
        return (
            f"Timed out while trying to fetch ({url_query}). wttr.in can be fussy; try again in a minute.",
            "",
        )
    except Exception as e:
        return "WTTR PROBLEMS: " + str(e), ""


plugin = AskBase(
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
