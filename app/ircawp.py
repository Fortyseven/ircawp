import argparse
import importlib

from rich import console as rich_console
from rich.traceback import install
from app.lib.thread_history import ThreadManager
from app.core import MessageRouter, PluginManager, MediaManager, URLExtractor

install(show_locals=True)

DEBUG = True

BANNER = r"""
[red] __[/red]
[red]|__|_______   ____  _____  __  _  ________[/red]
[bright_yellow]|  |\_  __ \_/ ___\ \__  \ \ \/ \/ /\____ \\[/bright_yellow]
[green]|  | |  | \/\  \___  / __ \_\     / |  |_) )[/green]
[blue]|__| |__|    \___  )(____  / \/\_/  |   __/[/blue]
[purple]                 \/      \/         |__|[/purple]

-=-=-=-=-=-=-=-=-= BOOTING =-=-=-=-=-=-=-=-
""".rstrip()


class Ircawp:
    """
    Main orchestrator for the ircawp bot.

    Wires together frontend, backend, plugins, and routing services.
    """

    def __init__(self, config: dict):
        """
        Initialize ircawp with the given configuration.

        Args:
            config: Application configuration dictionary
        """
        self.console = rich_console.Console()
        self.console.log(BANNER)

        self.config = config
        self.max_egest_length = self.config.get("max_egest_length", 3500)

        # Initialize backend
        self._init_backend()

        # Initialize image generation backend (optional)
        self._init_imagegen()

        # Initialize core services
        self.media_manager = MediaManager(
            console=self.console,
            media_dir=self.config.get("media_dir", "/tmp/ircawp_media"),
        )

        self.url_extractor = URLExtractor(console=self.console)

        self.plugin_manager = PluginManager(
            console=self.console,
            backend=self.backend,
            imagegen=self.imagegen,
            debug=DEBUG,
        )
        self.plugin_manager.load_plugins()

        self.message_router = MessageRouter(
            console=self.console,
            plugin_manager=self.plugin_manager,
            process_text_callback=self._process_text_message,
            # process_plugin_callback=self._process_plugin_message,
            egest_callback=self._egest_message,
            cleanup_media_callback=self.media_manager.cleanup_media_files,
            config=self.config,
            debug=DEBUG,
        )

        # Initialize frontend (must be last, as it may reference parent services)
        self._init_frontend()

    def _init_frontend(self) -> None:
        """Initialize the frontend from config."""
        frontend_id = self.config.get("frontend")
        self.console.log(f"- [yellow]Using frontend: {frontend_id}")

        frontend = getattr(
            importlib.import_module(f"app.frontends.{frontend_id}"),
            frontend_id.capitalize(),
        )

        self.frontend = frontend(console=self.console, parent=self, config=self.config)

    def _init_backend(self) -> None:
        """Initialize the backend from config."""
        backend_id = self.config.get("backend")
        self.console.log(f"- [yellow]Using backend: {backend_id}")

        backend = getattr(
            importlib.import_module(f"app.backends.{backend_id}"),
            backend_id.capitalize(),
        )

        self.backend = backend(
            console=self.console,
            parent=self,
            config=self.config,
        )

    def _init_imagegen(self) -> None:
        """Initialize the image generation backend from config (optional)."""
        if "imagegen_backend" in self.config:
            self.console.log(
                f"- [yellow]Setting up image generator:[/yellow] {self.config['imagegen_backend']}"
            )

            imagegen_backend_id = self.config["imagegen_backend"]
            imagegen_backend = getattr(
                importlib.import_module(f"app.media_backends.{imagegen_backend_id}"),
                imagegen_backend_id,
            )

            self.imagegen = imagegen_backend(self.backend)

            if hasattr(self.backend, "update_media_backend"):
                self.backend.update_media_backend(self.imagegen)
            else:
                self.backend.media_backend = self.imagegen
        else:
            self.console.log("- [red]Image generator disabled")
            self.imagegen = None
            if hasattr(self.backend, "update_media_backend"):
                self.backend.update_media_backend(None)
            else:
                self.backend.media_backend = None

    def ingestMessage(
        self,
        message,
        username,
        media=[],
        thread_history: ThreadManager = None,
        aux=None,
    ):
        """
        Receive a message from the frontend and put it into the queue.

        Args:
            message (str): Incoming message from the frontend.
            username (str): The username of the user who sent the message.
            media (list): Local file paths to attached media
            thread_history: Thread history manager instance
            aux (List, optional): Bundle of optional data needed to route the message back to the user.
        """
        self.message_router.ingest(message, username, media, thread_history, aux)

    def _egest_message(self, message: str, media: list, aux: dict) -> None:
        """
        Send a response to the frontend (internal callback).

        Args:
            message (str): Outgoing message to the frontend.
            media (list): Placeholder for media attachments.
            aux (list, optional): Bundle of optional data needed to route the message back to the user.
        """
        # Enforce size limit before sending to frontend to avoid transport errors
        try:
            if isinstance(message, str) and len(message) > self.max_egest_length:
                truncated_note = "\n\n[... message truncated due to size ...]"
                message = (
                    message[: self.max_egest_length - len(truncated_note)]
                    + truncated_note
                )

            self.frontend.egestEvent(message, media, aux)

        except Exception as e:
            # Never let frontend errors kill the queue thread; log and attempt a safe fallback
            try:
                self.console.log(
                    f"[red]Frontend egest error: {e}. Attempting to send a shortened notice."
                )
            except Exception:
                pass

            safe_msg = (
                "An error occurred delivering the response to the frontend. "
                "The content may be too large or invalid. Showing a shortened preview:\n\n"
            )
            preview = ""
            if isinstance(message, str):
                preview = message[: min(1000, len(message))]
            try:
                self.frontend.egestEvent(safe_msg + preview, media, aux)
            except Exception:
                # If even the fallback fails, swallow to keep the thread alive
                try:
                    self.console.log("[yellow]Fallback egest also failed; continuing.")
                except Exception:
                    pass

        # def _process_plugin_message(
        #     self, plugin_name: str, message: str, user_id: str, media: list = None
        # ) -> tuple:
        """
        Process a message directed to a plugin (internal callback).

        Args:
            plugin_name: Name of the plugin to execute
            message (str): The message text
            user_id (str): User ID who sent the message
            media: List of media file paths

        Returns:
            Tuple of (response_text, media_filename, skip_imagegen)
        """
        self.plugin_manager.execute_plugin(
            plugin_name=plugin_name, message=message, user_id=user_id, media=media or []
        )

    def _process_text_message(
        self, message: str, user_id: str, incoming_media: list = None, aux=None
    ) -> tuple:
        """
        Process a regular text message (internal callback).

        Args:
            message (str): The message text
            user_id (str): User ID who sent the message
            incoming_media (list): An array of local file path strings to incoming media.
            aux: Auxiliary routing data

        Returns:
            tuple[str, list[str]]: (response_text, tool_generated_image_paths)
        """
        # Augment message with URL content if URL is present
        message = self.url_extractor.augment_message_with_url(message)

        if incoming_media is None:
            incoming_media = []

        response, tool_images = self.backend.runInference(
            prompt=message,
            system_prompt=None,
            username=user_id,
            media=incoming_media,
            aux=aux,
        )

        return response, tool_images

    def start(self):
        """Start the bot: begin message processing and start the frontend."""
        self.console.log("[green on white]Here we go...")
        self.message_router.start()
        self.frontend.start()


def __main__():
    parser = argparse.ArgumentParser(description="ircawp bot runner")
    parser.add_argument(
        "--config",
        default="config.yml",
        help="Path to config file (default: config.yml)",
    )

    args = parser.parse_args()

    # Load configuration from the specified path
    cfg = None
    try:
        with open(args.config, "r") as f:
            import yaml

            cfg = yaml.safe_load(f)
    except FileNotFoundError:
        print(f"Config file not found: {args.config}")
        raise
    except Exception as e:
        print(f"Error loading config '{args.config}': {e}")
        raise

    print(f"* Using config file: {args.config}")

    ircawp = Ircawp(cfg)
    ircawp.start()
