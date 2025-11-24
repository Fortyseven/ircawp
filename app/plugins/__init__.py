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
    "translate",
    "uptime",
    "weather",
]

PLUGINS: dict[str, Any] = {}


def validatePlugin(plug, mod_name, console):
    invalid = False
    if not hasattr(plug, "plugin"):
        console.log(f"[red]ERROR: plugin {plug} does not have `plugin` object![/red]")
        invalid = True

    if invalid:
        plug_name = plug.__name__.split(".")[1]
        console.log(f"[red bold]ERROR: plugin {plug_name} was ignored![/]")
        PLUGINS.pop(plug_name)
    else:
        PLUGINS[mod_name] = PLUGINS[mod_name].plugin


def load(console):
    # load core plugins

    for plugin in CORE_PLUGINS:
        console.log("[purple]= Registering plugin:[/purple] " + plugin)

        PLUGINS[plugin] = importlib.import_module(
            f".{plugin}",
            "app.plugins",
        )

        validatePlugin(PLUGINS[plugin], plugin, console)

    # load user plugins
    # for file in os.listdir("plugins"):
    #     if file.endswith(".py") and not file.startswith("__"):
    #         console.log("= Registering plugin: " + file)

    #         mod_name = file[:-3]

    #         PLUGINS[mod_name] = importlib.import_module("plugins." + mod_name)

    #         validate_plugin(PLUGINS[mod_name], mod_namem, console)

    console.log("=========================")
