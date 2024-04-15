import os
import importlib
from rich import print

"""
iterate through the plugins directory for modules and import them
"""

PLUGINS = {}


def validate_plugin(plug):
    invalid = False
    if not hasattr(plug, "plugin"):
        print(
            f"[red]ERROR: plugin {plug} does not have `plugin` object![/red]"
        )
        invalid = True

    if invalid:
        plug_name = plug.__name__.split(".")[1]
        print(f"[red bold]ERROR: plugin {plug_name} was ignored![/]")
        PLUGINS.pop(plug_name)
    else:
        PLUGINS[mod_name] = PLUGINS[mod_name].plugin


for file in os.listdir("plugins"):
    if file.endswith(".py") and not file.startswith("__"):
        print("= Registering plugin: " + file)

        mod_name = file[:-3]

        PLUGINS[mod_name] = importlib.import_module("plugins." + mod_name)

        validate_plugin(PLUGINS[mod_name])


print("=========================")
