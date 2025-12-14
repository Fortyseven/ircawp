## IRCAWP Test Suite

This directory contains the automated test suite for the ircawp project, with initial focus on testing the plugin framework and tool registration system.

### Test Structure

```
tests/
├── conftest.py                 # Shared pytest fixtures and configuration
├── __init__.py
└── unit/
    ├── __init__.py
    ├── plugins/
    │   ├── __init__.py
    │   └── test_plugin_framework.py      # Plugin discovery, loading, validation
    └── tools/
        ├── __init__.py
        └── test_tool_framework.py        # Tool base, discovery, registration, ToolManager
```

### Running Tests

Run all tests:
```bash
pytest tests/
```

Run with verbose output:
```bash
pytest tests/ -v
```

Run only plugin tests:
```bash
pytest tests/unit/plugins/ -v
```

Run only tool tests:
```bash
pytest tests/unit/tools/ -v
```

Run with coverage:
```bash
pytest tests/ --cov=app --cov-report=html
```

### Test Markers

The tests use the following markers:

- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.plugin` - Plugin framework tests
- `@pytest.mark.tools` - Tool framework tests

### Fixtures

Common fixtures provided by `conftest.py`:

- **`mock_console`** - A mock Rich console for testing logging
- **`mock_backend`** - A mock LLM backend instance
- **`mock_media_backend`** - A mock media generation backend
- **`mock_llm_backend`** - A fully configured mock LLM backend
- **`test_config`** - Test configuration dictionary
- **`sample_plugin_module`** - A valid mock plugin module
- **`invalid_plugin_module`** - An invalid mock plugin module
- **`mock_tool`** - A fixture returning a test ToolBase class
- **`mock_plugin`** - A mock plugin instance
- **`clean_plugin_registry`** - Clean plugin registry for isolated tests
- **`clean_tool_registry`** - Clean tool registry for isolated tests

### Test Coverage

#### Plugin Framework (`test_plugin_framework.py`)

Tests cover:

1. **Plugin Discovery** (`TestDiscoverPlugins`)
   - Basic plugin discovery
   - Exclusion of internal modules (starting with `_`)
   - Exclusion of disabled directory
   - Sorted results

2. **Plugin Validation** (`TestValidatePlugin`)
   - Valid plugin validation
   - Invalid plugin handling (missing `plugin` attribute)
   - Error logging

3. **Plugin Loading** (`TestPluginLoad`)
   - Basic plugin loading with validation
   - Multiple plugin loading
   - Invalid plugin skipping
   - Sorted plugin discovery

4. **Integration** (`TestPluginIntegration`)
   - Full plugin lifecycle

#### Tool Framework (`test_tool_framework.py`)

Tests cover:

1. **ToolBase** (`TestToolBase`)
   - Initialization with dependencies
   - Default schema generation
   - Required schema fields
   - Expertise areas
   - Custom schema generation
   - Logging convenience method

2. **ToolResult** (`TestToolResult`)
   - Text-only results
   - Results with images
   - Empty results
   - Content detection

3. **Tool Discovery** (`TestToolDiscovery`)
   - Class-based tool discovery
   - Tool retrieval by name
   - Tool listing
   - Getting all tools
   - Handling nonexistent tools

4. **Decorated Tools** (`TestDecoratedTool`)
   - Tool creation with `@tool` decorator
   - Tool naming
   - Tool instantiation

5. **ToolManager** (`TestToolManagerInitialization`)
   - ToolManager initialization
   - Disabled tools handling
   - Media backend updates
   - Schema generation

### Adding New Tests

1. Create test files in the appropriate directory under `tests/unit/`
2. Use the provided fixtures from `conftest.py`
3. Mark tests with appropriate pytest markers
4. Follow the naming convention: `test_*.py` for files and `test_*` for functions
5. Group related tests into test classes

Example test structure:
```python
import pytest

pytestmark = pytest.mark.plugin  # or pytest.mark.tools

class TestNewFeature:
    """Tests for new feature."""

    def test_basic_behavior(self, mock_console):
        """Test basic behavior."""
        # Arrange
        # Act
        # Assert
        assert True

    def test_error_handling(self, mock_backend):
        """Test error handling."""
        # Test implementation
        pass
```

### Configuration

Pytest configuration is defined in `pyproject.toml`:
- Test paths: `tests/`
- Test discovery patterns: `test_*.py`, `*_test.py`
- Test classes: `Test*`
- Test functions: `test_*`
- Markers are defined for categorization

### Dependencies

Testing dependencies (from `pyproject.toml`):
- `pytest>=7.4.0` - Test framework
- `pytest-cov>=4.1.0` - Coverage reporting
- `pytest-mock>=3.11.1` - Mocking utilities
- `pytest-asyncio>=0.21.0` - Async test support

Install with:
```bash
pip install -e ".[test]"
```

Or from `requirements.txt`:
```bash
pip install pytest pytest-cov pytest-mock pytest-asyncio
```
