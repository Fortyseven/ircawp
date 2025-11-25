"""
Tools module for LLM backend function calling.

Tools can be used to extend LLM capabilities by providing access to external
functions, APIs, or data sources. Each tool is a separate submodule with a
common interface.
"""

from pathlib import Path
import importlib
from typing import Dict, Type
from .ToolBase import ToolBase

# Tool registry
_tools: Dict[str, Type[ToolBase]] = {}


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

                # Find ToolBase subclass in module
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (
                        isinstance(attr, type)
                        and issubclass(attr, ToolBase)
                        and attr is not ToolBase
                    ):
                        # Register tool by its name
                        tool_name = getattr(attr, "name", subdir.name)
                        _tools[tool_name] = attr
                        break
            except Exception as e:
                print(f"Failed to load tool from {subdir.name}: {e}")


def get_tool(name: str) -> Type[ToolBase] | None:
    """Get a tool class by name."""
    return _tools.get(name)


def list_tools() -> list[str]:
    """List all registered tool names."""
    return list(_tools.keys())


def get_all_tools() -> Dict[str, Type[ToolBase]]:
    """Get all registered tools."""
    return _tools.copy()


# Discover tools on import
discover_tools()
