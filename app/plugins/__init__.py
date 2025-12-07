import importlib
import pkgutil
from pathlib import Path
from typing import Any

"""
iterate through the plugins directory for modules and import them
"""

PLUGINS: dict[str, Any] = {}


def _discover_plugins() -> list[str]:
    """
    Discover available plugins by scanning the plugins directory.
    Excludes internal modules (starting with __) and the disabled directory.
    """
    plugins_dir = Path(__file__).parent
    discovered = []

    for importer, modname, ispkg in pkgutil.iter_modules([str(plugins_dir)]):
        # Skip internal modules and disabled directory
        if not modname.startswith("_") and modname != "disabled":
            discovered.append(modname)

    return sorted(discovered)


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

    discovered_plugins = _discover_plugins()

    for plugin in discovered_plugins:
        console.log("[white on green]+ Registering plugin: ", plugin)

        PLUGINS[plugin] = importlib.import_module(
            f".{plugin}",
            "app.plugins",
        )

        validatePlugin(PLUGINS[plugin], plugin, console)
