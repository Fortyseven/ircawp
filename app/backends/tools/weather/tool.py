"""
Example tool demonstrating the tool interface.

This tool returns a simple greeting message and optionally an image path.
"""

from ..ToolBase import tool
from pydantic import BaseModel, Field


@tool
def get_weather(location: str) -> str:
    """Get weather for a location."""
    return (
        f"The current weather in {location} is a sunny 120F with an expected tornado."
    )


# class ExampleTool(ToolBase):
#     """Example tool that demonstrates the tool interface."""

#     name = "weather"
#     description = "A tool that provides weather information"

#     def execute(self, **kwargs) -> ToolResult:
#         """
#         Execute the weather tool.

#         Args:
#             location (str, optional): Location to get weather for. Defaults to "World"

#         Returns:
#             ToolResult with weather information
#         """
#         location = kwargs.get("location", "World")

#         self.log(f"Executing with location={location}")

#         text = f"The current weather in {location} is a sunny 120F with an expected tornado."
#         images = []

#         return ToolResult(text=text, images=images)

#     def get_schema(self) -> Dict[str, Any]:
#         """Return the OpenAI function calling schema for this tool."""
#         return {
#             "type": "function",
#             "function": {
#                 "name": self.name,
#                 "description": self.description,
#                 "parameters": {
#                     "type": "object",
#                     "properties": {
#                         "location": {
#                             "type": "string",
#                             "description": "The location to get weather for",
#                         },
#                     },
#                     "required": [],
#                 },
#             },
#         }
