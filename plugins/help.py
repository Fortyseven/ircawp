"""
Help command, returns a list of registered slash commands.
"""

from backends import BaseBackend
from plugins.__AskBase import AskBase


def get_triggers(trigger: list) -> str:
    return "/" + ", /".join(trigger)


def help(query: str, backend: BaseBackend) -> tuple[str, str]:
    from plugins import PLUGINS  # lazy load

    groups = {}

    for plugin in PLUGINS:
        p = PLUGINS[plugin]
        if not hasattr(p, "group"):
            p.group = "misc"

        if p.group not in groups:
            groups[p.group] = []
        groups[p.group].append(plugin)

    output = ""

    # capitalize first letter
    groups = {k: groups[k] for k in sorted(groups.keys())}

    for group in groups:
        output += f"## {group.title()} ##\n"
        for plugin in groups[group]:
            output += f"`{get_triggers(PLUGINS[plugin].triggers)}` - {PLUGINS[plugin].description}\n"
        output += "\n"

    return "AVAILABLE SLASH COMMANDS :\n\n" + output, ""


plugin = AskBase(
    name="Help screen",
    description="Returns a list of registered /slash commands.",
    triggers=["help", "?"],
    system_prompt="",
    emoji_prefix="",
    msg_empty_query="No prompt provided",
    msg_exception_prefix="HELPFUL PROBLEMS",
    main=help,
    use_imagegen=False,
    group="system",
    prompt_required=False,
)
