import importlib
from typing import Any

"""
iterate through the plugins directory for modules and import them
"""

CORE_PLUGINS = [
    "askatherapist",
    "askhawkeye",
    "askjesus",
    "askspock",
    "help",
    "hn",
    "img",
    "geolocate",
    "news",
    "raw",
    "summarize",
    "tools",
    "translate",
    "uptime",
    "weather",
]

PLUGINS: dict[str, Any] = {}


def validatePlugin(plug, mod_name, console):
    invalid = False
    if not hasattr(plug, "plugin"):
        console.log(
            f"[red on green]ERROR: plugin {plug} does not have `plugin` object!"
        )
        invalid = True

    if invalid:
        plug_name = plug.__name__.split(".")[1]
        console.log(f"[red on green bold]ERROR: plugin {plug_name} was ignored!")
        PLUGINS.pop(plug_name)
    else:
        PLUGINS[mod_name] = PLUGINS[mod_name].plugin


def load(console):
    # load core plugins
    console.rule()
    console.log("- [white on green]Setting up plugins")

    for plugin in CORE_PLUGINS:
        console.log("[white on green]+ Registering plugin: ", plugin)

        PLUGINS[plugin] = importlib.import_module(
            f".{plugin}",
            "app.plugins",
        )

        validatePlugin(PLUGINS[plugin], plugin, console)
