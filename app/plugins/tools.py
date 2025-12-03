"""
Tools command, returns a list of registered LLM tool-calling functions.
"""

from app.backends.Ircawp_Backend import Ircawp_Backend
from app.media_backends.MediaBackend import MediaBackend
from .__PluginBase import PluginBase


def tools(
    query: str,
    media: list,
    backend: Ircawp_Backend,
    media_backend: MediaBackend = None,
) -> tuple[str, str]:
    """List all registered tool-calling functions available to the LLM."""

    # Check if backend has tools support
    if not hasattr(backend, "available_tools"):
        return "This backend doesn't support tool calling.", "", True, {}

    if not backend.available_tools:
        return "No tools are currently registered.", "", True, {}

    output = "Registered LLM tools:\n\n"

    # Sort tools by name for consistent output
    sorted_tools = sorted(backend.available_tools.items())

    for tool_name, tool_instance in sorted_tools:
        # Get the tool's description
        description = getattr(tool_instance, "description", "No description available")

        # Get the tool's schema to extract parameter information
        try:
            schema = tool_instance.get_schema()
            func_def = schema.get("function", {})
            params = func_def.get("parameters", {}).get("properties", {})

            output += f"----\n`{tool_name}` - {description}\n"

            if params:
                output += "  Parameters:\n"
                for param_name, param_def in params.items():
                    param_type = param_def.get("type", "unknown")
                    param_desc = param_def.get("description", "")
                    output += f"    • `{param_name}` ({param_type})"
                    if param_desc:
                        output += f": {param_desc}"
                    output += "\n"
            else:
                output += "  Parameters: None\n"

            output += "\n"

        except Exception as e:
            output += f"**{tool_name}**\n"
            output += f"  {description}\n"
            output += f"  (Error retrieving schema: {e})\n\n"

    total = len(backend.available_tools)
    return (
        f"{output}Total: {total} tool{'s' if total != 1 else ''} registered",
        "",
        True,
        {},
    )


plugin = PluginBase(
    name="Tools list",
    description="Returns a list of registered LLM tool-calling functions.",
    triggers=["tools", "functions"],
    system_prompt="",
    emoji_prefix="🔧",
    msg_empty_query="No prompt provided",
    msg_exception_prefix="TOOLS PROBLEMS",
    main=tools,
    use_imagegen=False,
    prompt_required=False,
)
