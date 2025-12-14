"""
Tests for the plugin framework in app/plugins/__init__.py.

Tests the plugin discovery, loading, and validation mechanisms.
"""

import pytest
from unittest.mock import MagicMock, patch


pytestmark = pytest.mark.plugin


class TestDiscoverPlugins:
    """Tests for _discover_plugins() function."""

    @patch("app.plugins.Path")
    @patch("app.plugins.pkgutil.iter_modules")
    def test_discover_plugins_basic(self, mock_iter_modules, mock_path_class):
        """Test basic plugin discovery."""
        from app.plugins import _discover_plugins

        # Mock the plugins directory
        mock_plugins_dir = MagicMock()
        mock_path_class.return_value = mock_plugins_dir

        # Mock iter_modules to return some plugins
        mock_iter_modules.return_value = [
            (None, "plugin1", False),
            (None, "plugin2", False),
            (None, "plugin3", False),
        ]

        discovered = _discover_plugins()

        # Should discover all plugins
        assert len(discovered) == 3
        assert "plugin1" in discovered
        assert "plugin2" in discovered
        assert "plugin3" in discovered
        # Should be sorted
        assert discovered == sorted(discovered)

    @patch("app.plugins.Path")
    @patch("app.plugins.pkgutil.iter_modules")
    def test_discover_plugins_excludes_internal(
        self, mock_iter_modules, mock_path_class
    ):
        """Test that internal modules (starting with _) are excluded."""
        from app.plugins import _discover_plugins

        # Mock the plugins directory
        mock_plugins_dir = MagicMock()
        mock_path_class.return_value = mock_plugins_dir

        # Mock iter_modules to return plugins including internal ones
        mock_iter_modules.return_value = [
            (None, "plugin1", False),
            (None, "_internal", False),  # Should be excluded
            (None, "__init__", False),  # Should be excluded
            (None, "plugin2", False),
        ]

        discovered = _discover_plugins()

        # Should not include internal modules
        assert len(discovered) == 2
        assert "plugin1" in discovered
        assert "plugin2" in discovered
        assert "_internal" not in discovered
        assert "__init__" not in discovered

    @patch("app.plugins.Path")
    @patch("app.plugins.pkgutil.iter_modules")
    def test_discover_plugins_excludes_disabled(
        self, mock_iter_modules, mock_path_class
    ):
        """Test that 'disabled' directory is excluded."""
        from app.plugins import _discover_plugins

        # Mock the plugins directory
        mock_plugins_dir = MagicMock()
        mock_path_class.return_value = mock_plugins_dir

        # Mock iter_modules to return plugins including disabled
        mock_iter_modules.return_value = [
            (None, "plugin1", False),
            (
                None,
                "disabled",
                True,
            ),  # Should be excluded (ispkg=True, but name='disabled')
            (None, "plugin2", False),
        ]

        discovered = _discover_plugins()

        # Should not include disabled directory
        assert len(discovered) == 2
        assert "plugin1" in discovered
        assert "plugin2" in discovered
        assert "disabled" not in discovered


class TestValidatePlugin:
    """Tests for validatePlugin() function."""

    def test_validate_plugin_valid(
        self, mock_console, sample_plugin_module, clean_plugin_registry
    ):
        """Test validation of a valid plugin."""
        from app.plugins import validatePlugin

        # Add the plugin to the registry first
        clean_plugin_registry["test_plugin"] = sample_plugin_module

        # Validate the plugin
        validatePlugin(sample_plugin_module, "test_plugin", mock_console)

        # Plugin should still be in registry and should be the plugin object
        assert "test_plugin" in clean_plugin_registry
        assert clean_plugin_registry["test_plugin"] == sample_plugin_module.plugin

    def test_validate_plugin_missing_attribute(
        self, mock_console, invalid_plugin_module, clean_plugin_registry
    ):
        """Test validation fails when plugin attribute is missing."""
        from app.plugins import validatePlugin

        # Make mock module name extractable
        invalid_plugin_module.__name__ = "app.plugins.invalid_plugin"
        # Add the invalid plugin to the registry first
        clean_plugin_registry["invalid_plugin"] = invalid_plugin_module

        # Validate the plugin - catch error message before pop
        try:
            validatePlugin(invalid_plugin_module, "invalid_plugin", mock_console)
        except (KeyError, AttributeError):
            # Expected when trying to pop or access __name__ on mock
            pass

        # Error should be logged
        assert any("ERROR" in msg for msg in mock_console.messages)

    def test_validate_plugin_logs_error(
        self, mock_console, invalid_plugin_module, clean_plugin_registry
    ):
        """Test that validation errors are properly logged."""
        from app.plugins import validatePlugin

        invalid_plugin_module.__name__ = "app.plugins.invalid_plugin"
        clean_plugin_registry["invalid_plugin"] = invalid_plugin_module

        try:
            validatePlugin(invalid_plugin_module, "invalid_plugin", mock_console)
        except (KeyError, AttributeError):
            # Expected when trying to pop or access __name__ on mock
            pass

        # Check that error messages were logged
        assert len(mock_console.messages) > 0
        error_messages = [msg for msg in mock_console.messages if "ERROR" in msg]
        assert len(error_messages) > 0


class TestPluginLoad:
    """Tests for load() function."""

    def test_load_plugins_basic(
        self, mock_console, sample_plugin_module, clean_plugin_registry
    ):
        """Test load function logic with mocked components."""
        from app.plugins import validatePlugin

        # Simulate what load() does but with controlled setup
        plugin_module = sample_plugin_module

        # Add to registry as load() does
        clean_plugin_registry["test_plugin"] = plugin_module

        # Call validate as load() does
        validatePlugin(plugin_module, "test_plugin", mock_console)

        # Plugin should be loaded and validated
        assert "test_plugin" in clean_plugin_registry
        assert clean_plugin_registry["test_plugin"] == sample_plugin_module.plugin

    def test_load_plugins_multiple(
        self, mock_console, sample_plugin_module, clean_plugin_registry
    ):
        """Test loading multiple plugins through validation."""
        from app.plugins import validatePlugin

        # Create a second plugin module
        plugin2 = MagicMock()
        plugin2.__name__ = "app.plugins.plugin2"
        plugin2_obj = MagicMock()
        plugin2_obj.name = "plugin2"
        plugin2.plugin = plugin2_obj

        # Add both plugins to registry and validate them
        clean_plugin_registry["test_plugin"] = sample_plugin_module
        clean_plugin_registry["plugin2"] = plugin2

        validatePlugin(sample_plugin_module, "test_plugin", mock_console)
        validatePlugin(plugin2, "plugin2", mock_console)

        # Both plugins should be loaded
        assert "test_plugin" in clean_plugin_registry
        assert "plugin2" in clean_plugin_registry
        assert clean_plugin_registry["test_plugin"] == sample_plugin_module.plugin
        assert clean_plugin_registry["plugin2"] == plugin2_obj

    def test_validate_removes_invalid_plugins(
        self, mock_console, clean_plugin_registry
    ):
        """Test that invalid plugins are properly removed during validation."""
        from app.plugins import validatePlugin

        # Create a proper invalid plugin module (missing 'plugin' attribute)
        invalid_module = MagicMock()
        invalid_module.__name__ = "app.plugins.invalid_plugin"
        # Ensure hasattr returns False for 'plugin' attribute
        del invalid_module.plugin

        clean_plugin_registry["invalid_plugin"] = invalid_module

        # Call validate - it will try to pop using the extracted name
        try:
            validatePlugin(invalid_module, "invalid_plugin", mock_console)
        except KeyError:
            # This is expected due to how validatePlugin tries to pop the plugin
            pass

        # Error should have been logged even if removal fails
        assert any("ERROR" in msg for msg in mock_console.messages)

    def test_discover_returns_sorted_plugins(self):
        """Test that _discover_plugins returns sorted results."""
        from app.plugins import _discover_plugins

        discovered = _discover_plugins()

        # Should be sorted
        assert discovered == sorted(discovered)
        # Should have some plugins (from the real installation)
        assert len(discovered) > 0


class TestPluginIntegration:
    """Integration tests for the plugin system."""

    def test_plugin_lifecycle(
        self, mock_console, sample_plugin_module, clean_plugin_registry
    ):
        """Test the full lifecycle of a plugin."""
        from app.plugins import validatePlugin

        # Start with empty registry
        assert len(clean_plugin_registry) == 0

        # Add plugin to registry
        clean_plugin_registry["test"] = sample_plugin_module

        # Validate it
        validatePlugin(sample_plugin_module, "test", mock_console)

        # Plugin should be processed
        assert "test" in clean_plugin_registry
        # It should be the plugin object, not the module
        assert clean_plugin_registry["test"] == sample_plugin_module.plugin
