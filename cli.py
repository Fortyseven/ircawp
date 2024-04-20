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
from app.lib.template_str import template_str

console = Console()

install(show_locals=False)

prompt = " ".join(sys.argv[1:])

if not prompt:
    print("Huh?")
    os._exit(-1)

backend_instance: Ircawp_Backend | None = None

match config.get("backend", "llamacpp"):
    # case "llamacpp":
    #     backend_instance = LlamaCppBackend()
    case "ollama":
        backend_instance = Ollama(console=console, config=config, parent=None)


print("\n----------------------------\n")
# print(f"- USER: [red]{prompt}[/]")

# if not prompt.startswith("/"):
#     pr = template_str(
#         config["system_prompt"], username="User", query=prompt.strip()
#     )
#     print(f"- PROMPT: [green]{pr}[/]")

response, media = backend_instance.runInference(user_prompt=prompt.strip())
print(f"- ASSISTANT: [blue]{response}[/]")

if media:
    print(f"- MEDIA: [green]{media}[/]")
    # dont load all this unless we _really_ need it
    # imagegen_instance: BaseImageGen = SDXS()
    # imagegen_instance.generateImage(media, "/tmp/temp.png")
    # os.system(f"catimg /tmp/temp.png")
