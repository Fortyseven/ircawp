"""
Tool management functionality for backends.

This module provides a reusable ToolManager class that handles:
- Tool initialization and registration
- Tool schema generation for OpenAI-compatible APIs
- Tool execution
- Media backend integration
"""

from typing import Dict, Any
from .tools import get_all_tools
from .tools.ToolBase import ToolResult


TOOL_RULES = """You have access to tools for gathering real-world information and performing actions.

CRITICAL RULES FOR TOOL USAGE:
1. ALWAYS use tools first when available - tools are the authoritative source for current data
2. You MUST call a tool in these situations:
   - When asked about current information (weather, news, events)
   - When asked to perform actions or calculations
   - When you need real-time or accurate data
   - When uncertain about facts - verify with tools
3. Do NOT rely on your training data for time-sensitive or current information
4. Use multiple tool calls if needed to fully answer a question
5. If a tool fails, report the error clearly and suggest alternatives if possible

TOOL OUTPUT HANDLING:
- Tool responses are authoritative and take precedence over your general knowledge
- Images from tools are displayed to the user - do not attempt to link to them unless tool provides a URL
- Wrap tool responses with <tool_response> tags for clarity
- Always report tool errors explicitly to the user
- If a tool cannot answer the question completely, tell the user what's missing

DECISION FRAMEWORK:
- User asks factual question → Call tool first
- User asks for action → Call tool
- User asks for calculations → Call calculator tool
- Uncertain about answer → Call tool to verify
- Have current knowledge in context → May use knowledge if very recent
"""

TOOL_CALL_TEMP = 0.1  # Low temperature for tool calls to ensure deterministic behavior


class ToolManager:
    """Manages tool initialization, execution, and schema generation."""

    def __init__(self, backend, console, config: Dict[str, Any]):
        """
        Initialize the ToolManager.

        Args:
            backend: The backend instance (e.g., Openai instance)
            console: Rich console for logging
            config: Configuration dict containing tool settings
        """
        self.backend = backend
        self.console = console
        self.config = config
        self.media_backend = None
        self.available_tools: Dict[str, Any] = {}
        self.tools_enabled = True
        self.tools_supported = True  # Track if endpoint supports tools

    def initialize(self, tools_enabled: bool = True) -> None:
        """
        Initialize and register available tools.

        Args:
            tools_enabled: Whether tools should be enabled
        """
        self.tools_enabled = tools_enabled

        if not tools_enabled:
            self.console.log("[red on cyan]Tools disabled in config")
            return

        all_tools = get_all_tools()
        self.console.log("[white on cyan]Initializing tools with schema validation...")

        for tool_name, tool_factory in all_tools.items():
            try:
                # Instantiate tool with access to backend and media backend
                # Works for both class-based and decorator-based tools
                tool_instance = tool_factory(
                    backend=self.backend,
                    media_backend=self.media_backend,
                    console=self.console,
                )
                self.available_tools[tool_name] = tool_instance

                # Validate schema
                schema = tool_instance.get_schema()
                if self._validate_schema(schema, tool_name):
                    self.console.log(f"- [green on cyan]Registered tool: {tool_name}")
                else:
                    self.console.log(
                        f"- [yellow on cyan]Registered tool (schema warnings): {tool_name}"
                    )

            except Exception as e:
                self.console.log(
                    f"[red on cyan]Failed to initialize tool {tool_name}: {e}"
                )
        # Log capability matrix if tools have expertise areas defined
        if self.available_tools:
            matrix = self.get_capability_matrix()
            if matrix:
                self.console.log(matrix)

    def update_media_backend(self, media_backend) -> None:
        """
        Update media_backend reference in all tools after it's created.

        Args:
            media_backend: The media backend instance to use for image generation
        """
        self.media_backend = media_backend

        # Update media_backend in all existing tool instances
        for tool_name, tool_instance in self.available_tools.items():
            tool_instance.media_backend = media_backend
            self.console.log(
                f"- [white on cyan]Updated media_backend for tool: {tool_name}"
            )

    def get_tool_schemas(self) -> list:
        """
        Get OpenAI function schemas for all available tools.

        Returns:
            List of tool schemas in OpenAI format
        """
        schemas = []
        for tool_name, tool in self.available_tools.items():
            schema = tool.get_schema()

            # Validate schema quality
            if not self._validate_schema(schema, tool_name):
                self.console.log(
                    f"[yellow on cyan]Warning: Schema issues detected for {tool_name}"
                )

            schemas.append(schema)
        return schemas

    def _validate_schema(self, schema: dict, tool_name: str) -> bool:
        """
        Validate tool schema for quality and completeness.

        Args:
            schema: The schema dict to validate
            tool_name: Name of the tool (for logging)

        Returns:
            True if schema passes validation
        """
        try:
            func_schema = schema.get("function", {})

            # Check for empty description
            desc = func_schema.get("description", "").strip()
            if not desc or len(desc) < 10:
                self.console.log(
                    f"[yellow on cyan]  - {tool_name}: Description is too short or empty"
                )
                return False

            # Check for parameters
            params = func_schema.get("parameters", {})
            props = params.get("properties", {})

            # Warn if no parameters (might be intentional, but worth noting)
            if not props:
                self.console.log(
                    f"[yellow on cyan]  - {tool_name}: No parameters defined (may be intentional)"
                )

            # Check parameter descriptions
            for param_name, param_def in props.items():
                param_desc = param_def.get("description", "").strip()
                if not param_desc:
                    self.console.log(
                        f"[yellow on cyan]  - {tool_name}.{param_name}: Missing parameter description"
                    )
                    return False

            return True
        except Exception as e:
            self.console.log(
                f"[red on cyan]  - Error validating {tool_name} schema: {e}"
            )
            return False

    def execute_tool(self, tool_name: str, arguments: dict) -> ToolResult:
        """
        Execute a tool and return its result.

        Args:
            tool_name: Name of the tool to execute
            arguments: Arguments to pass to the tool

        Returns:
            ToolResult containing the execution result
        """
        if tool_name not in self.available_tools:
            return ToolResult(text=f"Error: Tool '{tool_name}' not found")

        tool = self.available_tools[tool_name]
        try:
            result = tool.execute(**arguments)
            return result
        except Exception as e:
            self.console.log(f"[red on cyan]Error executing tool {tool_name}: {e}")
            return ToolResult(text=f"Error executing tool: {str(e)}")

    def is_enabled(self) -> bool:
        """Check if tools are enabled."""
        return self.tools_enabled

    def is_supported(self) -> bool:
        """Check if the endpoint supports tools."""
        return self.tools_supported

    def set_supported(self, supported: bool) -> None:
        """Set whether the endpoint supports tools."""
        self.tools_supported = supported

    def has_tools(self) -> bool:
        """Check if any tools are available."""
        return bool(self.available_tools)

    def get_capability_matrix(self) -> str:
        """
        Generate a tool capability matrix showing expertise areas for all tools.

        Returns:
            Formatted string describing which tools have expertise in which areas
        """
        # Collect all expertise areas and tools
        area_to_tools = {}
        tool_expertise = {}

        for tool_name, tool in self.available_tools.items():
            expertise_areas = (
                tool.get_expertise_areas()
                if hasattr(tool, "get_expertise_areas")
                else []
            )
            tool_expertise[tool_name] = expertise_areas

            for area in expertise_areas:
                if area not in area_to_tools:
                    area_to_tools[area] = []
                area_to_tools[area].append(tool_name)

        # Build formatted output
        if not area_to_tools:
            return ""

        matrix = "\nTool Expertise Matrix:\n"
        matrix += "─" * 60 + "\n"

        for area in sorted(area_to_tools.keys()):
            tools = area_to_tools[area]
            matrix += f"  {area:.<40} {', '.join(tools)}\n"

        matrix += "─" * 60 + "\n"

        return matrix
