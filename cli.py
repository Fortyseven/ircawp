#!/usr/bin/env python
import os
import sys
from lib.config import config
from rich import print
from backends.llamacpp import LlamaCppBackend as ircawp

prompt = " ".join(sys.argv[1:])

if not prompt:
    print("Huh?")
    os._exit(-1)

ircawp = ircawp()

print("\n----------------------------\n")
print("USER:\n " + prompt)
print("ASSISTANT:\n" + ircawp.query(prompt, raw=False) + "\n")
