from lib.config import config

# iterate through the functions directory for modules and import them

import os

FUNCTIONS = {}

for file in os.listdir("functions"):
    if file.endswith(".py") and not file.startswith("__"):
        print("Registering function: " + file)
        # import module from functions directory using "module" name
        import importlib

        mod_name = file[:-3]

        FUNCTIONS[mod_name] = importlib.import_module("functions." + mod_name)
        # FUNCTIONS[mod_name]["execute"] = FUNCTIONS[mod_name]["module"].execute


print(f"{FUNCTIONS=}")


# FUNCTIONS: dict = config["functions"]

# for func_key in FUNCTIONS:
#     print("Registering function: " + func_key)
#     # import module from functions directory using "module" name
#     import importlib

#     mod_name = FUNCTIONS[func_key]["module"]

#     FUNCTIONS[func_key]["module"] = importlib.import_module(
#         "functions." + FUNCTIONS[func_key]["module"]
#     )

#     FUNCTIONS[func_key]["execute"] = FUNCTIONS[func_key]["module"].execute
