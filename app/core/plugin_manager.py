"""Plugin discovery, loading, and execution."""

from typing import Dict, Optional, Tuple, List, Any
from rich.console import Console

import app.plugins as plugins
from app.plugins import PLUGINS


class PluginManager:
    """Manages plugin lifecycle: discovery, loading, and execution."""

    def __init__(
        self, console: Console, backend: Any, imagegen: Any = None, debug: bool = True
    ):
        """
        Initialize the plugin manager.

        Args:
            console: Rich console for logging
            backend: The LLM backend instance
            imagegen: The image generation backend instance (optional)
            debug: Whether to enable debug logging
        """
        self.console = console
        self.backend = backend
        self.imagegen = imagegen
        self.debug = debug
        self.plugins: Dict = {}

    def load_plugins(self) -> None:
        """Load all available plugins."""
        plugins.load(self.console)
        self.plugins = PLUGINS
        self.console.log(f"[green]Loaded {len(self.plugins)} plugins")

    def get_plugin(self, name: str) -> Optional[Any]:
        """
        Get a plugin by name.

        Args:
            name: The plugin name

        Returns:
            The plugin instance, or None if not found
        """
        return self.plugins.get(name)

    def has_plugin(self, name: str) -> bool:
        """
        Check if a plugin exists.

        Args:
            name: The plugin name

        Returns:
            True if plugin exists, False otherwise
        """
        return name in self.plugins

    def execute_plugin(
        self, plugin_name: str, message: str, user_id: str, media: List[str] = None
    ) -> Tuple[str, Optional[str], bool]:
        """
        Execute a plugin with the given parameters.

        Args:
            plugin_name: Name of the plugin to execute
            message: The message text (with plugin command removed)
            user_id: The user ID who triggered the plugin
            media: List of media file paths

        Returns:
            Tuple of (response_text, media_filename, skip_imagegen)
        """
        if not self.has_plugin(plugin_name):
            return f"Plugin {plugin_name} not found.", None, True

        self.console.log(f"[white on green]Processing plugin: {plugin_name}")

        # Remove the plugin command from the message
        clean_message = message.replace(f"/{plugin_name}", "").strip()

        if media is None:
            media = []

        # Execute the plugin
        response, outgoing_media, skip_imagegen, meta = self.plugins[
            plugin_name
        ].execute(
            query=clean_message,
            backend=self.backend,
            media=media,
            media_backend=self.imagegen,
        )

        if self.debug:
            self.console.log(
                f"[black on green]Plugin response: {response[0:10] if response else 'None'}, "
                f"media: {outgoing_media}, skip_imagegen: {skip_imagegen}"
            )

        return response, outgoing_media, skip_imagegen

    def is_plugin_command(self, message: str) -> bool:
        """
        Check if a message is a plugin command.

        Args:
            message: The message to check

        Returns:
            True if message starts with '/' and matches a plugin name
        """
        if not message.startswith("/"):
            return False

        plugin_name = message.split(" ")[0][1:]
        return self.has_plugin(plugin_name)

    def get_plugin_name_from_message(self, message: str) -> Optional[str]:
        """
        Extract plugin name from a message.

        Args:
            message: The message to parse

        Returns:
            Plugin name if found, None otherwise
        """
        if not message.startswith("/"):
            return None

        plugin_name = message.split(" ")[0][1:]
        return plugin_name if self.has_plugin(plugin_name) else None
