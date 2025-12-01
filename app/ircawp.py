import os
import argparse
import threading
import queue as q
import time
import importlib
from pathlib import Path

from rich import console as rich_console
from rich.traceback import install


from app.backends.Ircawp_Backend import Ircawp_Backend
from app.types import InfResponse
from app.lib.thread_history import ThreadManager

# Import MediaBackend base class for type hinting
from app.media_backends.MediaBackend import MediaBackend

import app.plugins as plugins
from app.plugins import PLUGINS


from app.frontends.Ircawp_Frontend import Ircawp_Frontend

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
    frontend: Ircawp_Frontend = None
    backend: Ircawp_Backend = None
    imagegen: MediaBackend = None
    queue_thread: threading.Thread
    queue: q.Queue
    console: rich_console.Console

    def __init__(self, config):
        self.console = rich_console.Console()

        self.console.log(BANNER)
        self.config = config
        # Maximum characters allowed in egested messages; prevent frontend errors
        self.max_egest_length = self.config.get("max_egest_length", 3500)

        # get config options, set up frontend, backend, and imagegen
        # process plugins, run setup for those needing it

        frontend_id = self.config.get("frontend")

        self.console.log(f"- [yellow]Using frontend: {frontend_id}")

        frontend = getattr(
            importlib.import_module(f"app.frontends.{frontend_id}"),
            frontend_id.capitalize(),
        )

        self.frontend = frontend(console=self.console, parent=self, config=self.config)

        #####

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

        #####

        if "imagegen_backend" in config:
            self.console.log(
                f"- [yellow]Setting up image generator:[/yellow] {config['imagegen_backend']}"
            )
            # import and set up image generation backend
            imagegen_backend_id = config["imagegen_backend"]
            imagegen_backend = getattr(
                importlib.import_module(f"app.media_backends.{imagegen_backend_id}"),
                imagegen_backend_id,
            )

            self.imagegen = imagegen_backend(self.backend)

            # Pass imagegen to backend so tools can access it
            if hasattr(self.backend, "update_media_backend"):
                self.backend.update_media_backend(self.imagegen)
            else:
                self.backend.media_backend = self.imagegen
        else:
            self.console.log("- [red]Image generator disabled")
            if hasattr(self.backend, "update_media_backend"):
                self.backend.update_media_backend(None)
            else:
                self.backend.media_backend = None

        #####

        plugins.load(self.console)

    def ingestMessage(
        self,
        message,
        username,
        media=[],
        thread_history: ThreadManager = None,
        aux=None,
    ):
        """
        Receives a message from the frontend and puts it into the
        queue.

        Args:
            message (str): Incoming message from the frontend.
            username (str): The username of the user who sent the message.
            media (list): Local file paths to attached media
            aux (List, optional): Bundle of optional data needed to route the message back to the user.
        """
        self.queue.put((message, username, media, thread_history, aux))

    def egestMessage(self, message: str, media: list, aux: dict):
        """
        Returns a response to the frontend.

        Args:
            message (str): Outgoing message to the frontend.
            media (list): Placeholder for media attachments.
            aux (list, optional): Bundle of optional data needed to route the message back to the user.
        """
        # enforce size limit before sending to frontend to avoid transport errors
        try:
            if isinstance(message, str) and len(message) > self.max_egest_length:
                truncated_note = "\n\n[... message truncated due to size ...]"
                message = (
                    message[: self.max_egest_length - len(truncated_note)]
                    + truncated_note
                )

            # this sends a response back to the frontend
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

    def processMessagePlugin(
        self, plugin: str, message: str, user_id: str, media: list = []
    ) -> InfResponse:
        """
        Process a message from the queue, directed towards a plugin
        instead of the standard inference backend.

        Args:
            message (str): _description_
            user_id (str): _description_

        Returns:
            InfResponse: _description_
        """
        self.console.log(f"[white on green]Processing plugin: {plugin}")
        message = message.replace(f"/{plugin} ", "").strip()
        response, outgoing_media, skip_imagegen = PLUGINS[plugin].execute(
            query=message,
            backend=self.backend,
            media=media,
            media_backend=self.imagegen,
        )

        if DEBUG:
            self.console.log(
                f"[black on green]Plugin response: {response[0:10]}, media: {outgoing_media}, skip_imagegen: {skip_imagegen}"
            )

        return response, outgoing_media, skip_imagegen

    def extractUrl(self, text: str) -> list:
        """
        Extract URLs from the given text.

        Args:
            text (str): The text to extract URLs from.
        Returns:
            list: A list of extracted URLs.
        """
        import re

        # Exclude < and > which are common delimiters (e.g. in Slack)
        url_pattern = re.compile(r"(https?://[^\s<>]+)")

        # FIXME: let's just grab the first one; we're having issues with the
        # message getting mangled if there's multiple...?!
        urls = url_pattern.findall(text)

        if not urls:
            return None

        url = urls[0]

        # Strip common trailing punctuation
        while url and url[-1] in ".,!?:;":
            url = url[:-1]

        # Handle trailing parenthesis (e.g. inside brackets)
        if url.endswith(")"):
            opens = url.count("(")
            closes = url.count(")")
            if closes > opens:
                url = url[:-1]

        return url

    def processMessageText(
        self, message: str, user_id: str, incoming_media: list, aux=None
    ) -> tuple[str, list[str]]:
        """
        Process a message from the queue.

        Args:
            message (str): _description_
            user_id (str): _description_
            incoming_media (list): An array of local file path strings to incoming media.

        Returns:
            tuple[str, list[str]]: (response_text, tool_generated_image_paths)
        """

        # extract URLs from prompt

        url = self.extractUrl(message)

        if url:
            from app.lib.network import fetchHtml

            content = fetchHtml(url, text_only=True, use_js=True)

            message = f"####{url} content: ```\n{content}\n```\n####\n\n{message}"

        response, tool_images = self.backend.runInference(
            prompt=message,
            system_prompt=None,
            username=user_id,
            media=incoming_media,
            aux=aux,
        )

        return response, tool_images

    # def generateImageSummary(self, text: str) -> str:
    #     """
    #     Generate a summary prompt for image generation based on the
    #     given text.

    #     Args:
    #         text (str): The text to summarize.
    #     """
    #     summary_prompt = (
    #         f"{config['llm'].get('imagegen_prompt')}\n####\n{text}\n"
    #         if config["llm"].get("imagegen_prompt")
    #         else f"Create a vivid, detailed image generation prompt based on this description:\n\n{text}\n\nProvide only the refined prompt, nothing else."
    #     )

    #     summary = self.backend.runInference(
    #         prompt=summary_prompt,
    #         system_prompt=summary_prompt,
    #     )

    #     self.console.log(f"[green]Generated image summary prompt: {summary}")

    #     return summary

    def messageQueueLoop(self) -> None:
        self.console.log("[green on white]Starting message queue thread...")

        thread_sleep = self.config.get("thread_sleep", 0.250)

        while True:
            inf_response: str = ""
            outgoing_media_filename: str = ""

            time.sleep(thread_sleep)

            if not self.queue.empty():
                self.console.rule("[white on purple]START QUEUE ITEM PROCESSING")

                # is_img_plugin = False
                skip_imagegen = True

                message, user_id, incoming_media, thread_history, aux = self.queue.get()
                message = message.strip()

                # self.console.log(f"[white on purple]thread: {thread_history}")

                outgoing_media_filename = ""

                if DEBUG:
                    self.console.log(
                        "[white on purple]Dequeued message:\n",
                        f"    [purple]|[/purple] '{message}'\n",
                        f"    [purple]|[/purple] from user {user_id},\n",
                        f"    [purple]|[/purple] with media {incoming_media},\n",
                        f"    [purple]|[/purple] and aux {aux}",
                    )

                try:
                    # is it a plugin?
                    if message.startswith("/"):
                        plugin_name = message.split(" ")[0][1:]
                        if plugin_name in PLUGINS:
                            self.console.log(
                                f"[white on green]Processing plugin: {plugin_name}"
                            )
                            inf_response, outgoing_media_filename, skip_imagegen = (
                                self.processMessagePlugin(
                                    plugin_name,
                                    message=message,
                                    user_id=user_id,
                                    media=incoming_media,
                                )
                            )
                        else:
                            inf_response = f"Plugin {plugin_name} not found."
                    # otherwise, process it as a regular text message
                    else:
                        inf_response, tool_images = self.processMessageText(
                            message, user_id, incoming_media, aux
                        )
                        # Use first tool-generated image if available
                        outgoing_media_filename = (
                            tool_images[0] if tool_images else None
                        )

                    if outgoing_media_filename and DEBUG:
                        self.console.log(
                            f"[yellow]Media filename: {outgoing_media_filename}"
                        )

                    # if skip_imagegen and DEBUG:
                    #     self.console.log(
                    #         "[yellow]Skipping image generation as requested."
                    #     )

                    self.console.log(
                        f"[white on green]Plugin returned {outgoing_media_filename}."
                    )

                    # we have a media filename and it exists, so we're good
                    if outgoing_media_filename and os.path.exists(
                        outgoing_media_filename
                    ):
                        self.console.log(
                            f"[blue on green]Media file provided from plugin: {outgoing_media_filename}"
                        )
                        pass

                finally:
                    # clean up incoming media files; they are no longer needed
                    for img_path in incoming_media:
                        try:
                            p = Path(img_path)
                            if p.is_file():
                                p.unlink()
                                self.console.log(
                                    f"[blue on white]Deleted temp media file: {img_path}"
                                )
                        except Exception as e:
                            self.console.log(
                                f"[red on white]Failed to delete temp media file '{img_path}': {e}"
                            )
                            continue

                # Always attempt to egest; protect the queue thread from frontend errors
                try:
                    self.egestMessage(
                        inf_response, [outgoing_media_filename or None], aux
                    )
                except Exception as e:
                    # egestMessage already handles errors, but double-guard here as well
                    try:
                        self.console.log(f"[red on white]Unhandled egest error: {e}")
                    except Exception:
                        pass
                if DEBUG:
                    self.console.log(
                        "[white on purple]egested response:\n",
                        f"    [purple]|[/purple] '{inf_response}'\n",
                        f"    [purple]|[/purple] with media '{outgoing_media_filename}'",
                    )
                self.console.rule("[white on purple]END QUEUE ITEM PROCESSING")

    def start(self):
        self.console.log("[green on white]Here we go...")
        self.queue = q.Queue()
        self.queue_thread = threading.Thread(target=self.messageQueueLoop, daemon=True)

        self.queue_thread.start()
        self.frontend.start()


def __main__():
    parser = argparse.ArgumentParser(description="ircawp bot runner")
    parser.add_argument(
        "--config",
        default="config.json",
        help="Path to config file (default: config.json)",
    )

    args = parser.parse_args()

    # Load configuration from the specified path
    # Without changing global state in app.lib.config
    cfg = None
    try:
        # Temporarily set environment to influence loader only if needed.
        # Prefer explicit path via local loader.
        with open(args.config, "r") as f:
            import json

            cfg = json.load(f)
    except FileNotFoundError:
        # Provide a clear error then exit
        print(f"Config file not found: {args.config}")
        raise
    except Exception as e:
        print(f"Error loading config '{args.config}': {e}")
        raise

    print(f"* Using config file: {args.config}")

    ircawp = Ircawp(cfg)
    ircawp.start()
