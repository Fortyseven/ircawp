"""Message queue management and routing."""

import queue as q
import threading
import time
from typing import Any, Callable, Optional, List
from rich.console import Console

from app.lib.thread_history import ThreadManager
from app.core.plugin_manager import PluginManager
from app.core.media_manager import MediaManager

# Path to most recently generated image
LAST_GENERATED_IMAGE_PATH = "/tmp/ircawp.last_imagegen_media.png"

# Global conversation history for + prefix continuation
_conversation_history: list[dict] = []
# Structure: [
#     {"role": "user", "content": "text", "media_data_uris": ["data:image/..."]},
#     {"role": "assistant", "content": "text"},
# ]


class MessageRouter:
    """Manages message queue and routing to appropriate handlers."""

    def __init__(
        self,
        console: Console,
        process_text_callback: Callable,
        media_manager: MediaManager,
        plugin_manager: PluginManager,
        egest_callback: Callable,
        config: dict,
        backend=None,
        debug: bool = True,
    ):
        """
        Initialize the message router.

        Args:
            console: Rich console for logging
            process_text_callback: Callback for processing text messages
            media_manager: MediaManager instance for managing media files
            plugin_manager: PluginManager instance for managing plugins
            egest_callback: Callback for sending responses to frontend
            config: Application configuration
            backend: Backend instance for accessing utilities like image conversion
            debug: Whether to enable debug logging
        """
        self.console = console
        self.process_text_callback = process_text_callback
        self.media_manager = media_manager
        self.plugin_manager = plugin_manager
        self.egest_callback = egest_callback
        self.config = config
        self.backend = backend
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

                # Handle ^ prefix: prepend last generated image to media list
                if message and message[0] == "^":
                    message = message[1:].strip()

                    # Check if last generated image exists
                    from pathlib import Path

                    last_image_path = Path(LAST_GENERATED_IMAGE_PATH)

                    if last_image_path.is_file():
                        # Prepend to media list (last image comes FIRST, user media AFTER)
                        incoming_media = [str(last_image_path)] + (incoming_media or [])

                        if self.debug:
                            self.console.log(
                                "[cyan on black]^ prefix: prepending last generated image to media"
                            )
                    else:
                        # Image doesn't exist - log warning but continue processing
                        self.console.log(
                            "[yellow on black]^ prefix detected but no last generated image found"
                        )

                # Check if plugin will need the most recent response (before we clear history)
                saved_most_recent_response = None
                if message.startswith("/"):
                    parts = message.split(" ", 1)
                    if len(parts) > 1 and parts[1].strip() == "+":
                        # Plugin wants to use most recent response - save it before clearing
                        if _conversation_history:
                            for msg in reversed(_conversation_history):
                                if msg.get("role") == "assistant":
                                    saved_most_recent_response = msg.get("content", "")
                                    break

                # Handle + prefix: continue previous conversation
                continue_conversation = False
                if message and message[0] == "+":
                    message = message[1:].strip()
                    continue_conversation = True

                    if self.debug:
                        self.console.log(
                            f"[cyan on black]+ prefix: continuing conversation with "
                            f"{len(_conversation_history)} prior messages"
                        )
                else:
                    # Clear conversation when user doesn't use + (starting fresh)
                    if _conversation_history:  # Only log if there was history
                        if self.debug:
                            self.console.log(
                                f"[cyan on black]Starting fresh conversation "
                                f"(cleared {len(_conversation_history)} prior messages)"
                            )
                        _conversation_history.clear()

                if self.debug:
                    self.console.log(
                        "[white on purple]Dequeued message:\n",
                        f"    [purple]|[/purple] '{message}'\n",
                        f"    [purple]|[/purple] from user {user_id},\n",
                        f"    [purple]|[/purple] with media {incoming_media},\n",
                        f"    [purple]|[/purple] and aux {aux}",
                    )

                # Convert incoming media to data URIs for conversation storage
                user_media_data_uris = []
                if incoming_media and self.backend:
                    for media_path in incoming_media:
                        data_uri = self.backend._image_to_data_uri(media_path)
                        if data_uri:
                            user_media_data_uris.append(data_uri)

                inf_response: str = ""
                outgoing_media_filename: Optional[str] = None
                skip_imagegen = True

                try:
                    # Check if this is a plugin command
                    if message.startswith("/"):
                        plugin_name = message.split(" ")[0][1:]

                        # Check if plugin arguments are just "+"
                        # This means "use the most recent assistant response"
                        parts = message.split(" ", 1)
                        if len(parts) > 1 and parts[1].strip() == "+":
                            # Use the saved response from before history was cleared
                            if saved_most_recent_response:
                                message = f"{parts[0]} {saved_most_recent_response}"

                                if self.debug:
                                    self.console.log(
                                        "[cyan on black]Plugin + argument: using most recent assistant response"
                                    )
                            else:
                                if self.debug:
                                    self.console.log(
                                        "[yellow on black]Plugin + argument used but no prior assistant response found"
                                    )

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
                    self.media_manager.cleanup_media_files(incoming_media)

                # Always store conversation turn (fresh start or continuation)
                # Store user message
                user_msg = {"role": "user", "content": message}
                if user_media_data_uris:
                    user_msg["media_data_uris"] = user_media_data_uris
                _conversation_history.append(user_msg)

                # Store assistant response
                _conversation_history.append(
                    {"role": "assistant", "content": inf_response}
                )

                if self.debug:
                    conv_type = (
                        "continuing" if continue_conversation else "starting new"
                    )
                    self.console.log(
                        f"[cyan on black]Stored conversation turn ({conv_type}). "
                        f"History now has {len(_conversation_history)} messages"
                    )

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
