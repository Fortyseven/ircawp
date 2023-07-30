from .HelpFunction import HelpFunction
from .ReverseFunction import ReverseFunction
from .SummaryFunction import SummaryFunction

__all__ = ["FUNCTIONS"]


# NOTE: no multi-word commands yet; we should fix this

FUNCTIONS = [
    {
        "name": "help",
        "description": "You're my only hope.",
        "executor": HelpFunction,
    },
    {
        "name": "?",
        "description": "You're my only hope.",
        "executor": HelpFunction,
        "hide": True,
    },
    {
        "name": "reverse",
        "description": ".gnirts a sesreveR",
        "executor": ReverseFunction,
    },
    {
        "name": "summary",
        "description": "Summarizes the given text on a webpage.",
        "executor": SummaryFunction,
    },
]
