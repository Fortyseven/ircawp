#!/usr/bin/env python
import os
import sys
import requests
from rich import print
from lib.reduce import reduce_html

prompt = " ".join(sys.argv[1:])

if not prompt:
    print("Huh?")
    os._exit(-1)


page_result = requests.get(prompt)

reduced, title = reduce_html(page_result.text)

print(reduced)

print("Size: ", len(reduced))
