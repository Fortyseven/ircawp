#!/usr/bin/env python3
import os
import sys
# from rich import print
import backends.llamacpp as ircawp

prompt = " ".join(sys.argv[1:])

if not prompt:
    print("Huh?")
    os._exit(-1)


ircawp = ircawp.IrcAwpLlamaCpp()

print(ircawp.query(prompt))
