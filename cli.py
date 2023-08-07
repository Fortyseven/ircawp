#!/usr/bin/env python
import os
import sys
from lib.config import config
from rich import print
from backends.llamacpp import LlamaCppBackend as ircawp
from lib.template_str import template_str
from rich.traceback import install

install(show_locals=False)

prompt = " ".join(sys.argv[1:])

if not prompt:
    print("Huh?")
    os._exit(-1)

ircawp = ircawp()

print("\n----------------------------\n")
print(f"- USER: [red]{prompt}[/]")

if not prompt.startswith("/"):
    pr = template_str(config["prompt"], username="User", query=prompt.strip())
    print(f"- PROMPT: [green]{pr}[/]")

print(f"- ASSISTANT: [blue]{ircawp.query(prompt, raw=False)}[/]")
