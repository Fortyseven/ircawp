#!/usr/bin/env python
"""
CLI for ircawp.

Runs the real bot with a console frontend (stdin/stdout) so the CLI
exercises the exact same pipeline as the Slack frontend (message queue,
routing, plugins, URL extraction, media):

    uv run python cli.py                 # interactive chat
    uv run python cli.py "some prompt"   # one-shot, then exit
"""

import os
import argparse
import yaml

from rich import print
from rich.traceback import install

from app.ircawp import Ircawp

install(show_locals=False)

# Parse command-line arguments
parser = argparse.ArgumentParser(description="CLI interface for IRCAWP")
parser.add_argument(
    "--config",
    type=str,
    default="config.yml",
    help="Path to configuration file (default: config.yml)",
)
parser.add_argument(
    "prompt",
    nargs="*",
    help="The prompt to send (omit to enter interactive chat mode)",
)

args = parser.parse_args()

# Load configuration from specified file
config_file = args.config
if not os.path.exists(config_file):
    print(f"[red]Error: Config file {config_file} not found.")
    os._exit(-1)

try:
    with open(config_file, "r") as f:
        config = yaml.safe_load(f)
except Exception as e:
    print(f"[red]Error loading config file: {e}")
    os._exit(-1)

prompt = " ".join(args.prompt).strip()

# Drive the real bot through the console frontend so the CLI behaves
# exactly like the Slack frontend.
config["frontend"] = "console"
if prompt:
    config["console_prompt"] = prompt

Ircawp(config).start()
