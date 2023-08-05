"""
Help command, returns a list of registered slash commands.
"""

from backends import BaseBackend

TRIGGERS = ["help", "?"]
DESCRIPTION = "Returns a list of registered slash commands."
GROUP="system"

def get_triggers(trigger: list) -> str:
    return "/" + ", /".join(trigger)


def execute(query: str, backend: BaseBackend) -> str:
    from plugins import PLUGINS  # lazy load

    groups = {}
    for plugin in PLUGINS:
        p = PLUGINS[plugin]
        if not hasattr(p, "GROUP"):
            p.GROUP = "misc"

        if p.GROUP not in groups:
            groups[p.GROUP] = []
        groups[p.GROUP].append(plugin)

    print(groups)

    output = ""

    # capitalize first letter
    groups = {k: groups[k] for k in sorted(groups.keys())}


    for group in groups:
        output += f"## {group.title()} ##\n"
        for plugin in groups[group]:
            output += f"`{get_triggers(PLUGINS[plugin].TRIGGERS)}` - {PLUGINS[plugin].DESCRIPTION}\n"
        output += "\n"

    return "AVAILABLE SLASH COMMANDS :\n\n" + output
