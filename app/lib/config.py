"""
load config.json and return it as a dict
"""

import os
import json

CONFIG_FILE = "config.json"


def load_config():
    if not os.path.exists(CONFIG_FILE):
        raise FileNotFoundError(f"Config file {CONFIG_FILE} not found.")

    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        raise Exception(f"Error loading config file: {e}")


config = load_config()
