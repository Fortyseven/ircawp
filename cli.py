#!/usr/bin/env python
import os
import sys

from rich import print
from rich.traceback import install
from rich.console import Console

# from imagegen.BaseImageGen import BaseImageGen
# from imagegen.SDXS import SDXS
from app.lib.config import config
from app.backends.openai import Openai
from app.backends.Ircawp_Backend import Ircawp_Backend
from app.plugins import PLUGINS


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
    response, media = PLUGINS[plugin].execute(
        query=message,
        backend=backend_instance,
    )

    return response, media


console = Console()

install(show_locals=False)

prompt = " ".join(sys.argv[1:])

if not prompt:
    print("Need a prompt.")
    os._exit(-1)

backend_instance: Ircawp_Backend | None = None

match config.get("backend", "ollama"):
    case "openai":
        backend_instance = Openai(console=console, config=config, parent=None)
    case _:
        raise ValueError(f"Invalid backend: {config['backend']}")

print("\n----------------------------\n")

import app.plugins as plugins

plugins.load(console)

print(f"- PROMPT: [yellow]{prompt}[/]")
response = ""

if prompt.startswith("/"):
    print(PLUGINS)
    plugin_name = prompt.split(" ")[0][1:]
    if plugin_name in PLUGINS:
        response, media_filename = processMessagePlugin(
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


print(f"- ASSISTANT:\n[blue]{response}[/]")

# if media:
# print(f"- MEDIA: [green]{media}[/]")
# dont load all this unless we _really_ need it
# imagegen_instance: BaseImageGen = SDXS()
# imagegen_instance.generateImage(media, "/tmp/temp.png")
# os.system(f"catimg /tmp/temp.png")
