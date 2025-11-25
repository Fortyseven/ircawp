"""
Example tool demonstrating the tool interface.

This tool returns a simple greeting message and optionally an image path.
"""

from ..ToolBase import ToolBase, ToolResult
from typing import Any, Dict


class ExampleTool(ToolBase):
    """Example tool that demonstrates the tool interface."""

    name = "example_tool"
    description = "An example tool that returns a greeting message"

    def execute(self, **kwargs) -> ToolResult:
        """
        Execute the example tool.

        Args:
            name (str, optional): Name to greet. Defaults to "World"
            include_image (bool, optional): Whether to include an example image path

        Returns:
            ToolResult with greeting text and optional image
        """
        name = kwargs.get("name", "World")
        include_image = kwargs.get("include_image", False)

        self.log(f"Executing with name={name}, include_image={include_image}")

        text = f"Hello, {name}! This is a response from the example tool."
        images = []

        if include_image:
            # In a real tool, this would be an actual image path
            images = ["/path/to/example/image.png"]
            text += " I've also included an example image."

        return ToolResult(text=text, images=images)

    def get_schema(self) -> Dict[str, Any]:
        """Return the OpenAI function calling schema for this tool."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "The name to greet"},
                        "include_image": {
                            "type": "boolean",
                            "description": "Whether to include an example image",
                        },
                    },
                    "required": [],
                },
            },
        }
