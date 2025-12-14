"""
Tests for the tool framework in app/backends/tools/.

Tests tool discovery, registration, schema generation, and ToolManager functionality.
"""

import pytest
from unittest.mock import MagicMock, patch


pytestmark = pytest.mark.tools


class TestToolBase:
    """Tests for ToolBase class."""

    def test_tool_base_initialization(
        self, mock_backend, mock_media_backend, mock_console
    ):
        """Test ToolBase initialization with dependencies."""
        from app.backends.tools.ToolBase import ToolBase

        class TestTool(ToolBase):
            name = "test_tool"
            description = "Test tool"

            def execute(self, **kwargs):
                pass

        tool = TestTool(
            backend=mock_backend, media_backend=mock_media_backend, console=mock_console
        )

        assert tool.backend == mock_backend
        assert tool.media_backend == mock_media_backend
        assert tool.console == mock_console
        assert tool.name == "test_tool"
        assert tool.description == "Test tool"

    def test_tool_base_default_schema(self, mock_tool):
        """Test default schema generation from ToolBase."""
        tool_class = mock_tool
        tool = tool_class()

        schema = tool.get_schema()

        # Check schema structure
        assert "type" in schema
        assert schema["type"] == "function"
        assert "function" in schema
        assert "name" in schema["function"]
        assert "description" in schema["function"]
        assert "parameters" in schema["function"]

        # Check function details
        assert schema["function"]["name"] == "test_tool"
        assert schema["function"]["description"] == "A test tool"

    def test_tool_base_schema_has_required_fields(self, mock_tool):
        """Test that generated schema includes required fields."""
        tool_class = mock_tool
        tool = tool_class()

        schema = tool.get_schema()
        params = schema["function"]["parameters"]

        assert "type" in params
        assert params["type"] == "object"
        assert "properties" in params
        assert "required" in params

    def test_tool_base_expertise_areas(self, mock_tool):
        """Test expertise areas can be retrieved."""
        tool_class = mock_tool
        tool = tool_class()

        expertise = tool.get_expertise_areas()

        assert isinstance(expertise, list)
        assert "testing" in expertise

    def test_tool_base_custom_schema(self):
        """Test custom schema generation in subclass."""
        from app.backends.tools.ToolBase import ToolBase

        class CustomTool(ToolBase):
            name = "custom_tool"
            description = "A custom tool"

            def execute(self, **kwargs):
                pass

            def get_schema(self):
                schema = super().get_schema()
                schema["function"]["parameters"] = {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Query parameter",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Result limit",
                        },
                    },
                    "required": ["query"],
                }
                return schema

        tool = CustomTool()
        schema = tool.get_schema()

        # Check custom properties
        props = schema["function"]["parameters"]["properties"]
        assert "query" in props
        assert "limit" in props
        assert schema["function"]["parameters"]["required"] == ["query"]

    def test_tool_base_log_convenience(self, mock_tool, mock_console):
        """Test log convenience method."""
        tool_class = mock_tool
        tool = tool_class(console=mock_console)

        tool.log("Test message")

        # Check that message was logged
        assert len(mock_console.messages) > 0
        assert any("Test message" in msg for msg in mock_console.messages)


class TestToolResult:
    """Tests for ToolResult class."""

    def test_tool_result_text_only(self):
        """Test ToolResult with text content."""
        from app.backends.tools.ToolBase import ToolResult

        result = ToolResult(text="Test result")

        assert result.text == "Test result"
        assert result.images == []
        assert result.has_content() is True

    def test_tool_result_with_images(self):
        """Test ToolResult with image paths."""
        from app.backends.tools.ToolBase import ToolResult

        images = ["/path/to/image1.png", "/path/to/image2.png"]
        result = ToolResult(text="Result with images", images=images)

        assert result.text == "Result with images"
        assert len(result.images) == 2
        assert result.images == images
        assert result.has_content() is True

    def test_tool_result_empty(self):
        """Test empty ToolResult."""
        from app.backends.tools.ToolBase import ToolResult

        result = ToolResult()

        assert result.text == ""
        assert result.images == []
        assert result.has_content() is False


class TestToolDiscovery:
    """Tests for tool discovery mechanism."""

    @patch("app.backends.tools.Path")
    @patch("app.backends.tools.importlib.import_module")
    def test_discover_tools_finds_class_based_tools(self, mock_import, mock_path_class):
        """Test discovery of class-based tools."""
        from app.backends.tools.ToolBase import ToolBase
        from app.backends.tools import _tools

        # Create a mock tool
        class MockTool(ToolBase):
            name = "mock_tool"
            description = "Mock tool"

            def execute(self, **kwargs):
                pass

        # Mock the tools directory and subdirectories
        mock_tools_dir = MagicMock()
        mock_subdir = MagicMock()
        mock_subdir.is_dir.return_value = True
        mock_subdir.name = "mock_tool"
        mock_tool_file = MagicMock()
        mock_tool_file.exists.return_value = True
        mock_subdir.__truediv__ = MagicMock(return_value=mock_tool_file)

        mock_tools_dir.iterdir.return_value = [mock_subdir]
        mock_path_class.return_value = mock_tools_dir

        # Mock the module
        mock_module = MagicMock()
        mock_module.MockTool = MockTool
        mock_import.return_value = mock_module

        # Clear and rediscover tools
        _tools.clear()

        from app.backends.tools import discover_tools

        discover_tools()

        # Tool should be discovered and registered
        assert "mock_tool" in _tools

    def test_get_tool(self, clean_tool_registry):
        """Test retrieving a tool by name."""
        from app.backends.tools import get_tool
        from app.backends.tools.ToolBase import ToolBase

        class TestGetTool(ToolBase):
            name = "test_get_tool"
            description = "For testing get_tool"

            def execute(self, **kwargs):
                pass

        # Add tool to registry
        clean_tool_registry["test_get_tool"] = TestGetTool

        tool = get_tool("test_get_tool")

        assert tool == TestGetTool

    def test_get_tool_nonexistent(self, clean_tool_registry):
        """Test retrieving a nonexistent tool returns None."""
        from app.backends.tools import get_tool

        tool = get_tool("nonexistent_tool")

        assert tool is None

    def test_list_tools(self, clean_tool_registry):
        """Test listing all tools."""
        from app.backends.tools import list_tools
        from app.backends.tools.ToolBase import ToolBase

        class Tool1(ToolBase):
            name = "tool1"
            description = "Tool 1"

            def execute(self, **kwargs):
                pass

        class Tool2(ToolBase):
            name = "tool2"
            description = "Tool 2"

            def execute(self, **kwargs):
                pass

        clean_tool_registry["tool1"] = Tool1
        clean_tool_registry["tool2"] = Tool2

        tools_list = list_tools()

        assert len(tools_list) == 2
        assert "tool1" in tools_list
        assert "tool2" in tools_list

    def test_get_all_tools(self, clean_tool_registry):
        """Test getting all tools."""
        from app.backends.tools import get_all_tools
        from app.backends.tools.ToolBase import ToolBase

        class Tool1(ToolBase):
            name = "tool1"
            description = "Tool 1"

            def execute(self, **kwargs):
                pass

        clean_tool_registry["tool1"] = Tool1

        all_tools = get_all_tools()

        assert isinstance(all_tools, dict)
        assert "tool1" in all_tools
        assert all_tools["tool1"] == Tool1


class TestDecoratedTool:
    """Tests for decorator-based tools."""

    def test_decorated_tool_creation(self):
        """Test creating a tool using @tool decorator."""
        from app.backends.tools.ToolBase import tool

        @tool(description="A test decorated tool")
        def my_tool(query: str) -> str:
            """Process a query."""
            return f"Result: {query}"

        # Check that tool is marked
        assert hasattr(my_tool, "_is_tool")
        assert hasattr(my_tool, "_tool_name")
        assert my_tool._is_tool is True

    def test_decorated_tool_name(self):
        """Test decorated tool has correct name."""
        from app.backends.tools.ToolBase import tool

        @tool(description="Test")
        def my_decorated_tool(query: str) -> str:
            """A test tool."""
            return query

        assert my_decorated_tool._tool_name == "my_decorated_tool"

    def test_decorated_tool_instantiation(self, mock_backend, mock_console):
        """Test that decorated tools can be instantiated."""
        from app.backends.tools.ToolBase import tool, DecoratedTool

        @tool(description="Custom description")
        def my_tool(query: str) -> str:
            """A tool that processes queries."""
            return f"Processed: {query}"

        # Create an instance by calling the factory function
        tool_instance = my_tool(backend=mock_backend, console=mock_console)

        # Should return a DecoratedTool instance
        assert isinstance(tool_instance, DecoratedTool)
        assert tool_instance.name == "my_tool"
        assert tool_instance.description == "Custom description"


class TestToolManagerInitialization:
    """Tests for ToolManager initialization and setup."""

    def test_tool_manager_init(self, mock_backend, mock_console, test_config):
        """Test ToolManager initialization."""
        from app.backends.tools_manager import ToolManager

        manager = ToolManager(mock_backend, mock_console, test_config)

        assert manager.backend == mock_backend
        assert manager.console == mock_console
        assert manager.config == test_config
        assert manager.available_tools == {}
        assert manager.tools_enabled is True

    def test_tool_manager_disabled(self, mock_backend, mock_console, test_config):
        """Test ToolManager with tools disabled."""
        from app.backends.tools_manager import ToolManager

        manager = ToolManager(mock_backend, mock_console, test_config)
        manager.initialize(tools_enabled=False)

        assert manager.tools_enabled is False
        assert manager.available_tools == {}

    def test_tool_manager_update_media_backend(
        self, mock_backend, mock_media_backend, mock_console, test_config, mock_tool
    ):
        """Test updating media backend in ToolManager."""
        from app.backends.tools_manager import ToolManager

        manager = ToolManager(mock_backend, mock_console, test_config)

        # Register a tool first
        tool_instance = mock_tool(backend=mock_backend, console=mock_console)
        manager.available_tools["test_tool"] = tool_instance

        # Update media backend
        manager.update_media_backend(mock_media_backend)

        assert manager.media_backend == mock_media_backend
        # Tool should also have updated media backend
        assert tool_instance.media_backend == mock_media_backend

    def test_tool_manager_get_schemas(
        self, mock_backend, mock_console, test_config, mock_tool
    ):
        """Test getting schemas from ToolManager."""
        from app.backends.tools_manager import ToolManager

        manager = ToolManager(mock_backend, mock_console, test_config)

        # Add a tool
        tool_instance = mock_tool(backend=mock_backend, console=mock_console)
        manager.available_tools["test_tool"] = tool_instance

        schemas = manager.get_tool_schemas()

        assert isinstance(schemas, list)
        assert len(schemas) == 1
        assert schemas[0]["type"] == "function"
        assert schemas[0]["function"]["name"] == "test_tool"
