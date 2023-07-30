import numpy as np
import re
import random


def wc(string: str):
    return len(string.split())


def cleanup(prompt: str, response: str) -> str:
    # if prompt ends in punctuation, strip it
    if prompt[-1:] in ".?!":
        response = response.replace(prompt, "")

    # Uppercase the first letter, always
    response = response.strip()
    response = response[0].upper() + response[1:]

    # Split response up by newline
    lines = response.split("\n")

    # Remove empty lines
    lines = [x for x in lines if x != ""]

    # Ensure no lines repeat themselves
    indexes = np.unique(lines, return_index=True)[1]
    lines = [lines[index] for index in sorted(indexes)]

    # Ensure the last line has punctuation.
    if not lines[-1][-1] in '.?!"':
        ender = random.choice("!?.")
        lines[-1] += ender

    # axe anything less than 3 words
    lines = filter(lambda x: wc(x) >= 3, lines)

    response = " ".join(lines)

    return response
