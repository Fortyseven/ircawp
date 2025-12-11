"""
load config.yml and return it as a dict
"""

import os
import yaml

CONFIG_FILE = "config.yml"


def load_config():
    if not os.path.exists(CONFIG_FILE):
        raise FileNotFoundError(f"Config file {CONFIG_FILE} not found.")

    try:
        with open(CONFIG_FILE, "r") as f:
            return yaml.safe_load(f)
    except Exception as e:
        raise Exception(f"Error loading config file: {e}")


config = load_config()
