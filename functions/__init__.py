import os
from lib.config import config
import importlib
from rich import print

"""
iterate through the functions directory for modules and import them
"""

FUNCTIONS = {}


def validate_function(func):
    invalid = False
    if not hasattr(func, "TRIGGERS"):
        print(
            f"[red]ERROR: Function {func} does not have a `TRIGGERS` attribute![/red]"
        )
        invalid = True

    if not hasattr(func, "DESCRIPTION"):
        print(
            f"[red]ERROR: Function {func} does not have a `DESCRIPTION` attribute![/red]"
        )
        invalid = True

    if not hasattr(func, "execute"):
        print(f"[red]ERROR: Function {func} does not have an`execute` method![/red]")
        invalid = True

    if invalid:
        func_name = func.__name__.split('.')[1]
        print(f"[red bold]ERROR: Function {func_name} was ignored![/]")
        FUNCTIONS.pop(func_name)


for file in os.listdir("functions"):
    if file.endswith(".py") and not file.startswith("__"):
        print("= Registering function: " + file)

        mod_name = file[:-3]

        FUNCTIONS[mod_name] = importlib.import_module("functions." + mod_name)
        validate_function(FUNCTIONS[mod_name])

print("=========================")
