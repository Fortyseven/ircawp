#!/usr/bin/env python3
import os
import sys
from rich import print
import ircawp

prompt = ' '.join(sys.argv[1:])

if not prompt:
    print("Huh?")
    os._exit(-1)


ircawp = ircawp.IrcAwp()

print(ircawp.query(prompt))
