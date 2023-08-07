import os
import importlib
from rich import print

"""
iterate through the plugins directory for modules and import them
"""

PLUGINS = {}


def validate_plugin(plug):
    invalid = False
    if not hasattr(plug, "TRIGGERS"):
        print(
            f"[red]ERROR: plugin {plug} does not have a `TRIGGERS` attribute![/red]"
        )
        invalid = True

    if not hasattr(plug, "DESCRIPTION"):
        print(
            f"[red]ERROR: plugin {plug} does not have a `DESCRIPTION` attribute![/red]"
        )
        invalid = True

    if not hasattr(plug, "execute"):
        print(
            f"[red]ERROR: plugin {plug} does not have an`execute` method![/red]"
        )
        invalid = True

    if invalid:
        plug_name = plug.__name__.split(".")[1]
        print(f"[red bold]ERROR: plugin {plug_name} was ignored![/]")
        PLUGINS.pop(plug_name)


for file in os.listdir("plugins"):
    if file.endswith(".py") and not file.startswith("__"):
        print("= Registering plugin: " + file)

        mod_name = file[:-3]

        PLUGINS[mod_name] = importlib.import_module("plugins." + mod_name)
        validate_plugin(PLUGINS[mod_name])

print("=========================")
