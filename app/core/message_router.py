"""Message queue management and routing."""

import queue as q
import threading
import time
from typing import Any, Callable, Optional, List
from rich.console import Console

from app.lib.thread_history import ThreadManager
from app.core.plugin_manager import PluginManager


class MessageRouter:
    """Manages message queue and routing to appropriate handlers."""

    def __init__(
        self,
        console: Console,
        process_text_callback: Callable,
        plugin_manager: PluginManager,
        egest_callback: Callable,
        cleanup_media_callback: Callable,
        config: dict,
        debug: bool = True,
    ):
        """
        Initialize the message router.

        Args:
            console: Rich console for logging
            process_text_callback: Callback for processing text messages
            process_plugin_callback: Callback for processing plugin commands
            egest_callback: Callback for sending responses to frontend
            cleanup_media_callback: Callback for cleaning up media files
            config: Application configuration
            debug: Whether to enable debug logging
        """
        self.console = console
        self.process_text_callback = process_text_callback
        # self.process_plugin_callback = process_plugin_callback
        self.plugin_manager = plugin_manager
        self.egest_callback = egest_callback
        self.cleanup_media_callback = cleanup_media_callback
        self.config = config
        self.debug = debug

        self.queue: q.Queue = None
        self.queue_thread: threading.Thread = None
        self.thread_sleep = config.get("thread_sleep", 0.250)

    def start(self) -> None:
        """Start the message queue processing thread."""
        self.console.log("[green on white]Starting message queue thread...")
        self.queue = q.Queue()
        self.queue_thread = threading.Thread(
            target=self._message_queue_loop, daemon=True
        )
        self.queue_thread.start()

    def ingest(
        self,
        message: str,
        username: str,
        media: List[str] = None,
        thread_history: Optional[ThreadManager] = None,
        aux: Any = None,
    ) -> None:
        """
        Add a message to the processing queue.

        Args:
            message: The message text
            username: Username of the sender
            media: List of media file paths
            thread_history: Thread history manager instance
            aux: Auxiliary data for routing response back to user
        """
        if media is None:
            media = []

        self.queue.put((message, username, media, thread_history, aux))

    def _message_queue_loop(self) -> None:
        """
        Main queue processing loop.

        Continuously processes messages from the queue and routes them
        to appropriate handlers (plugins or text processing).
        """
        while True:
            time.sleep(self.thread_sleep)

            if not self.queue.empty():
                self.console.rule("[white on purple]START QUEUE ITEM PROCESSING")

                # Get message from queue
                message, user_id, incoming_media, thread_history, aux = self.queue.get()
                message = message.strip()

                if self.debug:
                    self.console.log(
                        "[white on purple]Dequeued message:\n",
                        f"    [purple]|[/purple] '{message}'\n",
                        f"    [purple]|[/purple] from user {user_id},\n",
                        f"    [purple]|[/purple] with media {incoming_media},\n",
                        f"    [purple]|[/purple] and aux {aux}",
                    )

                inf_response: str = ""
                outgoing_media_filename: Optional[str] = None
                skip_imagegen = True

                try:
                    # Check if this is a plugin command
                    if message.startswith("/"):
                        plugin_name = message.split(" ")[0][1:]

                        # Delegate to plugin processing callback
                        (
                            inf_response,
                            outgoing_media_filename,
                            skip_imagegen,
                        ) = self.plugin_manager.execute_plugin(
                            plugin_name=plugin_name,
                            message=message,
                            user_id=user_id,
                            media=incoming_media or [],
                        )

                        if self.debug:
                            self.console.log(
                                f"[white on green]Plugin returned {inf_response, outgoing_media_filename}."
                            )

                    # Otherwise, process as regular text message
                    else:
                        inf_response, tool_images = self.process_text_callback(
                            message=message,
                            user_id=user_id,
                            incoming_media=incoming_media,
                            aux=aux,
                        )

                        # Use first tool-generated image if available
                        outgoing_media_filename = (
                            tool_images[0] if tool_images else None
                        )

                    if outgoing_media_filename and self.debug:
                        self.console.log(
                            f"[yellow]Media filename: {outgoing_media_filename}"
                        )

                except Exception as e:
                    self.console.log(f"[red]Error processing message: {e}")
                    inf_response = "An error occurred processing your request."
                    outgoing_media_filename = None

                finally:
                    # Clean up incoming media files - they are no longer needed
                    self.cleanup_media_callback(incoming_media)

                # Always attempt to egest; protect the queue thread from frontend errors
                try:
                    self.egest_callback(
                        message=inf_response,
                        media=[outgoing_media_filename]
                        if outgoing_media_filename
                        else [None],
                        aux=aux,
                    )
                except Exception as e:
                    # egestMessage already handles errors, but double-guard here
                    try:
                        self.console.log(f"[red on white]Unhandled egest error: {e}")
                    except Exception:
                        pass

                if self.debug:
                    self.console.log(
                        "[white on purple]egested response:\n",
                        f"    [purple]|[/purple] '{inf_response}'\n",
                        f"    [purple]|[/purple] with media '{outgoing_media_filename}'",
                    )

                self.console.rule("[white on purple]END QUEUE ITEM PROCESSING")
