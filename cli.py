#!/usr/bin/env python
import os
import argparse
import yaml

from rich import print
from rich.traceback import install
from rich.console import Console

# from imagegen.BaseImageGen import BaseImageGen
# from imagegen.SDXS import SDXS
from app.backends.openai import Openai
from app.backends.Ircawp_Backend import Ircawp_Backend
from app.plugins import PLUGINS
import app.plugins as plugins


def processMessagePlugin(plugin: str, message: str, user_id: str, backend_instance):
    """
    Process a message from the queue, directed towards a plugin
    instead of the standard inference backend.

    Args:
        message (str): _description_
        user_id (str): _description_

    Returns:
        InfResponse: _description_
    """
    console.log(f"Processing plugin: {plugin}")
    message = message.replace(f"/{plugin} ", "").strip()
    response = PLUGINS[plugin].execute(
        query=message,
        backend=backend_instance,
        media=[],
    )

    return response


console = Console()

install(show_locals=False)

# Parse command-line arguments
parser = argparse.ArgumentParser(description="CLI interface for IRCAWP")
parser.add_argument(
    "--config",
    type=str,
    default="config.yml",
    help="Path to configuration file (default: config.yml)",
)
parser.add_argument("prompt", nargs="*", help="The prompt to send")

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

prompt = " ".join(args.prompt)

if not prompt:
    print("Need a prompt.")
    os._exit(-1)

backend_instance: Ircawp_Backend | None = None

backend_instance = Openai(console=console, config=config, parent=None)

print("\n----------------------------\n")

plugins.load(console)

print(f"- PROMPT: [yellow]{prompt}")
response = ""

if prompt.startswith("/"):
    print(PLUGINS)
    plugin_name = prompt.split(" ")[0][1:]
    if plugin_name in PLUGINS:
        response = processMessagePlugin(
            plugin=plugin_name,
            message=prompt,
            user_id="CLI",
            backend_instance=backend_instance,
        )
    else:
        response = f"Plugin {plugin_name} not found."
        media_filename = ""
else:
    response = backend_instance.runInference(
        system_prompt=config["llm"]["system_prompt"], prompt=prompt.strip()
    )


print(f"- ASSISTANT:\n[blue]{response}")
