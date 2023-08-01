from lib.config import config

FUNCTIONS: dict = config["functions"]

for func_key in FUNCTIONS:
    print("Registering function: " + func_key)
    # import module from functions directory using "module" name
    import importlib

    mod_name = FUNCTIONS[func_key]["module"]

    FUNCTIONS[func_key]["module"] = importlib.import_module(
        "functions." + FUNCTIONS[func_key]["module"]
    )

    FUNCTIONS[func_key]["execute"] = FUNCTIONS[func_key]["module"].execute
