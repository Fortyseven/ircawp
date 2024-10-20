#!/usr/bin/env python
import os
import sys

from rich import print
from rich.traceback import install
from rich.console import Console

# from imagegen.BaseImageGen import BaseImageGen
# from imagegen.SDXS import SDXS
from app.lib.config import config
from app.backends.ollama import Ollama
from app.backends.Ircawp_Backend import Ircawp_Backend

console = Console()

install(show_locals=False)

prompt = " ".join(sys.argv[1:])

if not prompt:
    print("Need a prompt.")
    os._exit(-1)

backend_instance: Ircawp_Backend | None = None

match config.get("backend", "ollama"):
    case "ollama":
        backend_instance = Ollama(console=console, config=config, parent=None)
    case _:
        raise ValueError(f"Invalid backend: {config['backend']}")

print("\n----------------------------\n")

response = backend_instance.runInference(
    system_prompt=config["llm"]["system_prompt"], prompt=prompt.strip()
)

print(f"- ASSISTANT: [blue]{response}[/]")

# if media:
# print(f"- MEDIA: [green]{media}[/]")
# dont load all this unless we _really_ need it
# imagegen_instance: BaseImageGen = SDXS()
# imagegen_instance.generateImage(media, "/tmp/temp.png")
# os.system(f"catimg /tmp/temp.png")
