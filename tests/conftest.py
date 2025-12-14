"""
Shared pytest fixtures for testing the ircawp project.

This module provides common fixtures for mocking dependencies like backend,
console, and media_backend objects used throughout the application.
"""

import pytest
from unittest.mock import MagicMock
from io import StringIO
from typing import Dict, Any


class MockConsole:
    """Mock Rich console for testing."""

    def __init__(self):
        self.messages = []
        self.output = StringIO()

    def log(self, message="", *args, **kwargs):
        """Mock log method."""
        self.messages.append(str(message))
        self.output.write(str(message) + "\n")

    def rule(self, *args, **kwargs):
        """Mock rule method."""
        self.messages.append("---")

    def get_output(self) -> str:
        """Get all logged output."""
        return self.output.getvalue()

    def clear(self):
        """Clear messages."""
        self.messages = []
        self.output = StringIO()


@pytest.fixture
def mock_console():
    """Provide a mock console for testing."""
    return MockConsole()


@pytest.fixture
def mock_backend():
    """Provide a mock backend instance."""
    backend = MagicMock()
    backend.console = MockConsole()
    backend.name = "test_backend"
    backend.config = {}
    return backend


@pytest.fixture
def mock_media_backend():
    """Provide a mock media backend instance."""
    media_backend = MagicMock()
    media_backend.console = MockConsole()
    media_backend.name = "test_media_backend"
    media_backend.config = {}
    return media_backend


@pytest.fixture
def test_config() -> Dict[str, Any]:
    """Provide a test configuration dictionary."""
    return {
        "tools_enabled": True,
        "model": "gpt-4",
        "temperature": 0.7,
        "max_tokens": 2000,
    }


@pytest.fixture
def mock_llm_backend(mock_console, test_config):
    """Provide a fully mocked LLM backend."""
    backend = MagicMock()
    backend.console = mock_console
    backend.config = test_config
    backend.name = "openai"
    backend.model = "gpt-4"
    # Mock inference method
    backend.infer = MagicMock(return_value="Test response")
    backend.infer_with_tools = MagicMock(return_value=("Test response", []))
    return backend


@pytest.fixture
def mock_plugin():
    """Provide a mock plugin instance."""
    plugin = MagicMock()
    plugin.name = "test_plugin"
    plugin.description = "Test plugin"
    plugin.triggers = ["test"]
    plugin.execute = MagicMock(return_value=("Test response", "", True, {}))
    return plugin


@pytest.fixture
def mock_tool():
    """Provide a mock tool instance."""
    from app.backends.tools.ToolBase import ToolBase

    class TestTool(ToolBase):
        name = "test_tool"
        description = "A test tool"
        expertise_areas = ["testing"]

        def execute(self, **kwargs):
            from app.backends.tools.ToolBase import ToolResult

            return ToolResult(text="Test tool executed")

        def get_schema(self) -> Dict[str, Any]:
            schema = super().get_schema()
            schema["function"]["parameters"] = {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The query to test",
                    }
                },
                "required": ["query"],
            }
            return schema

    return TestTool


@pytest.fixture
def sample_plugin_module():
    """
    Provide a sample plugin module for testing plugin loading.

    Returns a module-like object that has a plugin attribute.
    """
    module = MagicMock()
    module.__name__ = "app.plugins.test_plugin"

    # Create a mock plugin object
    plugin = MagicMock()
    plugin.name = "test_plugin"
    plugin.description = "A test plugin"
    plugin.triggers = ["test"]
    plugin.execute = MagicMock(return_value=("Test response", "", True, {}))

    module.plugin = plugin
    return module


@pytest.fixture
def invalid_plugin_module():
    """
    Provide an invalid plugin module (missing plugin attribute).

    Returns a module-like object without a plugin attribute.
    """
    module = MagicMock()
    module.__name__ = "app.plugins.invalid_plugin"
    # Explicitly remove the plugin attribute
    del module.plugin
    return module


@pytest.fixture
def clean_plugin_registry():
    """
    Provide a clean plugin registry for testing.

    Returns the PLUGINS registry and clears it before and after the test.
    """
    from app.plugins import PLUGINS

    original_plugins = PLUGINS.copy()
    PLUGINS.clear()

    yield PLUGINS

    PLUGINS.clear()
    PLUGINS.update(original_plugins)


@pytest.fixture
def clean_tool_registry():
    """
    Provide a clean tool registry for testing.

    Returns the _tools registry and clears it before and after the test.
    """
    from app.backends.tools import _tools

    original_tools = _tools.copy()
    _tools.clear()

    yield _tools

    _tools.clear()
    _tools.update(original_tools)
