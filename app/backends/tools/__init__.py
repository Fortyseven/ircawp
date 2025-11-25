"""
Tools module for LLM backend function calling.

Tools can be used to extend LLM capabilities by providing access to external
functions, APIs, or data sources. Each tool is a separate submodule with a
common interface. Supports both class-based and decorator-based (@tool) tools.
"""

from pathlib import Path
import importlib
from typing import Dict, Type, Callable
from .ToolBase import ToolBase, tool, DecoratedTool

__all__ = [
    "ToolBase",
    "tool",
    "DecoratedTool",
    "get_tool",
    "list_tools",
    "get_all_tools",
]

# Tool registry - stores tool factories (classes or decorated functions)
_tools: Dict[str, Type[ToolBase] | Callable] = {}


def discover_tools():
    """Automatically discover and register all tools in subdirectories."""
    tools_dir = Path(__file__).parent

    for subdir in tools_dir.iterdir():
        if not subdir.is_dir() or subdir.name.startswith("_"):
            continue

        # Look for tool.py in each subdirectory
        tool_file = subdir / "tool.py"
        if tool_file.exists():
            try:
                # Import the tool module
                module_name = f"app.backends.tools.{subdir.name}.tool"
                module = importlib.import_module(module_name)

                # Find all ToolBase subclasses and @tool decorated functions
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)

                    # Check for class-based tools
                    if (
                        isinstance(attr, type)
                        and issubclass(attr, ToolBase)
                        and attr is not ToolBase
                        and attr is not DecoratedTool
                    ):
                        tool_name = getattr(attr, "name", subdir.name)
                        _tools[tool_name] = attr

                    # Check for decorator-based tools
                    elif callable(attr) and hasattr(attr, "_is_tool"):
                        tool_name = getattr(attr, "_tool_name", attr_name)
                        _tools[tool_name] = attr

            except Exception as e:
                print(f"Failed to load tool from {subdir.name}: {e}")


def get_tool(name: str) -> Type[ToolBase] | Callable | None:
    """Get a tool factory by name."""
    return _tools.get(name)


def list_tools() -> list[str]:
    """List all registered tool names."""
    return list(_tools.keys())


def get_all_tools() -> Dict[str, Type[ToolBase] | Callable]:
    """Get all registered tool factories."""
    return _tools.copy()


# Discover tools on import
discover_tools()
