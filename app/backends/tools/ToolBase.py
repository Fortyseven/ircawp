"""
Base class for all LLM tools.

Tools extend LLM capabilities by providing access to external functions,
APIs, or data sources. Supports both decorator-based (@tool) and class-based
tool definitions, mimicking LangChain's approach.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Callable, get_type_hints
from pathlib import Path
from pydantic import BaseModel
import inspect


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
    expertise_areas: List[str] = []  # Areas of expertise for this tool

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
        schema = {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        }
        # Ensure description is never empty - this improves tool calling
        if not schema["function"]["description"]:
            schema["function"]["description"] = f"Execute the {self.name} tool"
        return schema

    def log(self, message: str):
        """Convenience method to log messages."""
        if self.console:
            self.console.log(f"[Tool:{self.name}] {message}")

    def get_expertise_areas(self) -> List[str]:
        """
        Return the areas of expertise for this tool.

        Can be overridden by subclasses to define custom expertise areas.

        Returns:
            List of expertise area strings (e.g., ['mathematics', 'calculations'])
        """
        return self.expertise_areas


class DecoratedTool(ToolBase):
    """
    Wrapper for decorator-based tools.

    This class wraps functions decorated with @tool to make them compatible
    with the ToolBase interface.
    """

    def __init__(
        self,
        func: Callable,
        name: str | None = None,
        description: str | None = None,
        args_schema: type[BaseModel] | None = None,
        expertise_areas: List[str] | None = None,
        backend=None,
        media_backend=None,
        console=None,
    ):
        """
        Initialize a decorated tool.

        Args:
            func: The function to wrap
            name: Tool name (defaults to function name)
            description: Tool description (defaults to function docstring)
            args_schema: Pydantic model for input validation
            expertise_areas: Areas of expertise for this tool
            backend: LLM backend instance
            media_backend: Media generation backend
            console: Rich console for logging
        """
        super().__init__(backend, media_backend, console)

        self._func = func
        self.name = name or func.__name__
        self.description = description or (func.__doc__ or "").strip()
        self.args_schema = args_schema
        self.expertise_areas = expertise_areas or []

        # Generate schema from function signature
        self._generate_schema()

    def _generate_schema(self):
        """Generate OpenAI function schema from function signature."""
        sig = inspect.signature(self._func)
        type_hints = get_type_hints(self._func)

        properties = {}
        required = []

        # Extract parameter descriptions from docstring if available
        param_docs = self._extract_param_docs()

        for param_name, param in sig.parameters.items():
            # Skip injected parameters
            if param_name in ("backend", "media_backend", "console"):
                continue

            param_type = type_hints.get(param_name, str)
            # Try to get description from docstring, fallback to param name
            param_desc = param_docs.get(param_name, f"Parameter: {param_name}")

            # Basic type mapping
            json_type = "string"
            if param_type is int:
                json_type = "integer"
            elif param_type is float:
                json_type = "number"
            elif param_type is bool:
                json_type = "boolean"

            properties[param_name] = {"type": json_type, "description": param_desc}

            # Mark as required if no default value
            if param.default == inspect.Parameter.empty:
                required.append(param_name)

        # If args_schema provided, use it instead
        if self.args_schema:
            schema = self.args_schema.model_json_schema()
            properties = schema.get("properties", {})
            required = schema.get("required", [])

        self._schema = {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }

    def _extract_param_docs(self) -> dict:
        """
        Extract parameter descriptions from function docstring.

        Looks for Args section in docstring and parses parameter descriptions.

        Returns:
            Dict mapping parameter names to their descriptions
        """
        param_docs = {}
        doc = inspect.getdoc(self._func)
        if not doc:
            return param_docs

        # Simple parser for Google-style docstrings
        in_args = False
        lines = doc.split("\n")

        for i, line in enumerate(lines):
            if line.strip().lower().startswith("args:"):
                in_args = True
                continue
            elif in_args and line.strip() and not line[0].isspace():
                # End of Args section
                break
            elif in_args:
                # Parse "    param_name: description" format
                stripped = line.strip()
                if ":" in stripped and stripped[0].isalpha():
                    parts = stripped.split(":", 1)
                    param_name = parts[0].strip()
                    param_desc = parts[1].strip() if len(parts) > 1 else ""
                    if param_desc:
                        param_docs[param_name] = param_desc

        return param_docs

    def execute(self, **kwargs) -> ToolResult:
        """Execute the wrapped function."""
        # Inject backend services if function accepts them
        sig = inspect.signature(self._func)
        if "backend" in sig.parameters:
            kwargs["backend"] = self.backend
        if "media_backend" in sig.parameters:
            kwargs["media_backend"] = self.media_backend
        if "console" in sig.parameters:
            kwargs["console"] = self.console

        result = self._func(**kwargs)

        # Convert result to ToolResult if needed
        if isinstance(result, ToolResult):
            return result
        elif isinstance(result, str):
            return ToolResult(text=result)
        else:
            return ToolResult(text=str(result))

    def get_schema(self) -> Dict[str, Any]:
        """Return the generated schema."""
        return self._schema


def tool(
    name: str | None = None,
    description: str | None = None,
    args_schema: type[BaseModel] | None = None,
    expertise_areas: List[str] | None = None,
):
    """
    Decorator to create a tool from a function.

    Usage:
        @tool
        def my_tool(query: str) -> str:
            '''Search for information.'''
            return f"Results for {query}"

        @tool(name="custom_name", description="Custom description")
        def another_tool(x: int, y: int) -> str:
            '''Add two numbers.'''
            return str(x + y)

        # With expertise areas
        @tool(
            description="Get weather for a location",
            expertise_areas=["weather", "climate", "forecasting"]
        )
        def weather(location: str) -> str:
            '''Get weather for a location.'''
            return f"Weather in {location}: 72°F"

        # With Pydantic schema and expertise
        class MyInput(BaseModel):
            location: str = Field(description="City name")
            units: str = Field(default="celsius")

        @tool(
            args_schema=MyInput,
            expertise_areas=["weather", "meteorology"]
        )
        def weather_advanced(location: str, units: str = "celsius") -> str:
            '''Get weather with custom units.'''
            return f"Weather in {location}: 72°{units[0].upper()}"

    Args:
        name: Override the function name
        description: Override the function docstring
        args_schema: Pydantic model for input validation
        expertise_areas: List of areas this tool has expertise in

    Returns:
        Decorated function that can be used as a tool
    """

    def decorator(func: Callable) -> DecoratedTool:
        # Return a factory function that creates the tool when called
        def tool_factory(backend=None, media_backend=None, console=None):
            return DecoratedTool(
                func=func,
                name=name,
                description=description,
                expertise_areas=expertise_areas,
                args_schema=args_schema,
                backend=backend,
                media_backend=media_backend,
                console=console,
            )

        # Store metadata on the factory
        tool_factory._is_tool = True
        tool_factory._tool_name = name or func.__name__
        tool_factory._tool_func = func

        return tool_factory

    # Support both @tool and @tool()
    if callable(name):
        func = name
        name = None
        return decorator(func)

    return decorator
