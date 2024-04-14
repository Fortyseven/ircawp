#!/usr/bin/env python
import os
import sys
from lib.config import config
from rich import print
from backends import OllamaBackend, LlamaCppBackend
from lib.template_str import template_str
from rich.traceback import install

install(show_locals=False)

prompt = " ".join(sys.argv[1:])

if not prompt:
    print("Huh?")
    os._exit(-1)

backend_instance = None

match config.get("backend", "llamacpp"):
    case "llamacpp":
        backend_instance = LlamaCppBackend()
    case "ollama":
        backend_instance = OllamaBackend()


print("\n----------------------------\n")
print(f"- USER: [red]{prompt}[/]")

if not prompt.startswith("/"):
    pr = template_str(
        config["system_prompt"], username="User", query=prompt.strip()
    )
    print(f"- PROMPT: [green]{pr}[/]")

print(f"- ASSISTANT: [blue]{backend_instance.query(prompt)}[/]")
