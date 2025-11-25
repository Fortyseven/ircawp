"""
Base class for all LLM tools.

Tools extend LLM capabilities by providing access to external functions,
APIs, or data sources. Each tool must implement the execute() method and
can return both text and images.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List
from pathlib import Path


class ToolResult:
    """Represents the result of a tool execution."""

    def __init__(self, text: str = "", images: List[str | Path] = None):
        """
        Initialize tool result.

        Args:
            text: Text content to return to the LLM
            images: List of image file paths (can be local paths or URLs)
        """
        self.text = text
        self.images = images or []

    def has_content(self) -> bool:
        """Check if result has any content."""
        return bool(self.text or self.images)


class ToolBase(ABC):
    """
    Base class for all tools.

    Tools have access to:
    - backend: The LLM backend instance (for making additional inferences)
    - media_backend: The media generation backend (for image generation)
    - console: Rich console for logging
    """

    # Tool metadata (override in subclasses)
    name: str = "base_tool"
    description: str = "Base tool class"

    def __init__(self, backend=None, media_backend=None, console=None):
        """
        Initialize tool with access to backend services.

        Args:
            backend: The LLM backend instance
            media_backend: The media generation backend
            console: Rich console for logging
        """
        self.backend = backend
        self.media_backend = media_backend
        self.console = console

    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """
        Execute the tool with given parameters.

        Args:
            **kwargs: Tool-specific parameters

        Returns:
            ToolResult containing text and/or images
        """
        pass

    def get_schema(self) -> Dict[str, Any]:
        """
        Return OpenAI function calling schema for this tool.

        Override this to define the parameters your tool accepts.

        Returns:
            Dict containing the function schema in OpenAI format
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        }

    def log(self, message: str):
        """Convenience method to log messages."""
        if self.console:
            self.console.log(f"[Tool:{self.name}] {message}")
