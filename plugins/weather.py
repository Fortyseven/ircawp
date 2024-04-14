"""
Bot plugin to summarize a web page using a smaller,
faster model than the default chat model.
"""

import json
import requests

from backends.BaseBackend import BaseBackend

TRIGGERS = ["weather"]
DESCRIPTION = "Get the weather for a location from wttr.in"


def process_weather_json(json_text: str) -> str:
    """
    https://wttr.in/:help
    """
    # decode
    try:
        weather_data = json.loads(json_text)

        if not weather_data["current_condition"]:
            return "Error: no current condition data."

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

        return f"Weather for {where}: {desc} at 🌡 {temps}, winds 🌬 {wind_dir} at {wind_mph}mph ({wind_kph}kph), 💦 humidity at {humidity}%. (⏰ As of {observed}, local.)"

    except json.decoder.JSONDecodeError:
        return "Error: could not decode JSON."


def execute(query: str, backend: BaseBackend) -> tuple[str, str]:
    if not query.strip():
        return "No query provided for weather plugin.", ""

    try:
        # with open("w.json", "r") as f:
        #     return process_weather_json(f.read())

        url_query = f"https://wttr.in/{query}?format=j1"
        response = requests.get(url_query, timeout=12, allow_redirects=True)

        if response.status_code >= 400:
            return (
                f"Error: code ({response.status_code}) for ({url_query})",
                "",
            )

        return process_weather_json(response.text), ""
    except requests.exceptions.Timeout:
        return (
            f"Timed out while trying to fetch ({url_query}). wttr.in can be fussy; try again in a minute.",
            "",
        )
    except Exception as e:
        return "BIG PROBLEMS: " + str(e), ""
