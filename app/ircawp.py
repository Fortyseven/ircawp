import os
import threading
import queue as q
import time
import importlib
from pathlib import Path

from rich import console as rich_console
from rich.traceback import install


from app.backends.Ircawp_Backend import Ircawp_Backend
from app.types import InfResponse

# Import MediaBackend base class for type hinting
from app.media_backends.MediaBackend import MediaBackend

import app.plugins as plugins
from app.plugins import PLUGINS

from app.lib.config import config
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

# temp config


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

        # get config options, set up frontend, backend, and imagegen
        # process plugins, run setup for those needing it

        frontend_id = self.config.get("frontend")

        self.console.log(f"- [yellow]Using frontend: {frontend_id}[/yellow]")

        frontend = getattr(
            importlib.import_module(f"app.frontends.{frontend_id}"),
            frontend_id.capitalize(),
        )

        self.frontend = frontend(
            console=self.console,
            parent=self,
            config=self.config.get("frontends", {}).get(frontend_id, {}),
        )

        #####

        backend_id = self.config.get("backend")

        self.console.log(f"- [yellow]Using backend: {backend_id}[/yellow]")

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
        else:
            self.console.log("- [red]Image generator disabled[/red]")

        #####

        self.console.log("- [yellow]Setting up plugins[/yellow]")

        plugins.load(self.console)

    def ingestMessage(self, message, username, media=[], aux=None):
        """
        Receives a message from the frontend and puts it into the
        queue.

        Args:
            message (str): Incoming message from the frontend.
            username (str): The username of the user who sent the message.
            media (list): Local file paths to attached media
            aux (List, optional): Bundle of optional data needed to route the message back to the user.
        """
        self.queue.put((message, username, media, aux))

    def egestMessage(self, message: str, media: list, aux: dict):
        """
        Returns a response to the frontend.

        Args:
            message (str): Outgoing message to the frontend.
            media (list): Placeholder for media attachments.
            aux (list, optional): Bundle of optional data needed to route the message back to the user.
        """
        # this sends a response back to the frontend
        self.frontend.egestEvent(message, media, aux)

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
        self.console.log(f"Processing plugin: {plugin}")
        message = message.replace(f"/{plugin} ", "").strip()
        response, outgoing_media, skip_imagegen = PLUGINS[plugin].execute(
            query=message,
            backend=self.backend,
            media=media,
        )

        if DEBUG:
            self.console.log(
                f"Plugin response: {response[0:10]}, media: {outgoing_media}, skip_imagegen: {skip_imagegen}"
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
        self, message: str, user_id: str, incoming_media: list
    ) -> InfResponse:
        """
        Process a message from the queue.

        Args:
            message (str): _description_
            user_id (str): _description_
            incoming_media (list): An array of local file path strings to incoming media.

        Returns:
            InfResponse: _description_
        """

        # extract URLs from prompt

        url = self.extractUrl(message)

        if url:
            from app.lib.network import fetchHtml

            content = fetchHtml(url, text_only=True, use_js=True)

            message = f"####{url} content: ```\n{content}\n```\n####\n\n{message}"

        response = self.backend.runInference(
            prompt=message,
            system_prompt=None,
            username=user_id,
            media=incoming_media,
        )

        return response

    def generateImageSummary(self, text: str) -> str:
        """
        Generate a summary prompt for image generation based on the
        given text.

        Args:
            text (str): The text to summarize.
        """
        summary_prompt = f"{config['llm'].get('imagegen_prompt')}\n####\n{text}\n"

        summary = self.backend.runInference(
            prompt=summary_prompt,
            system_prompt="You are an expert at creating vivid image descriptions.",
            username="imagegen_summary_bot",
        )

        self.console.log(f"[green]Generated image summary prompt:[/green] {summary}")

        return summary

    def messageQueueLoop(self) -> None:
        if DEBUG:
            self.console.log("Starting message queue thread...")

        thread_sleep = config.get("thread_sleep", 0.250)
        while True:
            inf_response: str = ""
            outgoing_media_filename: str = ""

            time.sleep(thread_sleep)

            if not self.queue.empty():
                self.console.rule("[white on purple]START QUEUE ITEM PROCESSING")

                is_img_plugin = False
                skip_imagegen = False

                message, user_id, incoming_media, aux = self.queue.get()
                message = message.strip()

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
                            inf_response, outgoing_media_filename, skip_imagegen = (
                                self.processMessagePlugin(
                                    plugin_name,
                                    message=message,
                                    user_id=user_id,
                                    media=incoming_media,
                                )
                            )
                            if plugin_name == "img":
                                is_img_plugin = True
                        else:
                            inf_response = f"Plugin {plugin_name} not found."
                            outgoing_media_filename = ""
                    # otherwise, process it as a regular text message
                    else:
                        inf_response = self.processMessageText(
                            message, user_id, incoming_media
                        )
                        outgoing_media_filename = None

                    if not skip_imagegen and outgoing_media_filename and DEBUG:
                        self.console.log(
                            f"[yellow]Media filename: {outgoing_media_filename}[/yellow]"
                        )

                    if skip_imagegen and DEBUG:
                        self.console.log(
                            "[yellow]Skipping image generation as requested.[/yellow]"
                        )

                    self.console.log(
                        f"[red]Plugin returned {outgoing_media_filename}.[/red]"
                    )

                    # we have a media filename and it exists, so we're good
                    if outgoing_media_filename and os.path.exists(
                        outgoing_media_filename
                    ):
                        self.console.log(
                            f"[green]Media file provided from plugin:[/green] {outgoing_media_filename}"
                        )
                        pass
                    else:
                        # otherwise pass the response as a prompt and save the resulting filename

                        self.console.log(
                            f"[yellow]Media file {outgoing_media_filename} not found, generating from response using {self.imagegen}.[/yellow]"
                        )
                        if self.imagegen and not skip_imagegen:
                            self.console.log("[yellow]Generating image...[/yellow]")
                            imagegen_summary = self.generateImageSummary(inf_response)
                            if is_img_plugin:
                                inf_response = imagegen_summary
                            outgoing_media_filename = self.imagegen.execute(
                                prompt=imagegen_summary
                            )
                finally:
                    # clean up incoming media files; they are no longer needed
                    for img_path in incoming_media:
                        try:
                            p = Path(img_path)
                            if p.is_file():
                                p.unlink()
                                self.console.log(
                                    f"[blue]Deleted temp media file: {img_path}[/blue]"
                                )
                        except Exception as e:
                            self.console.log(
                                f"[yellow]Failed to delete temp media file '{img_path}': {e}[/yellow]"
                            )
                            continue

                self.egestMessage(inf_response, [outgoing_media_filename or None], aux)
                if DEBUG:
                    self.console.log(
                        "[purple]egested response:\n",
                        f"    [purple]|[/purple] '{inf_response}'\n",
                        f"    [purple]|[/purple] with media '{outgoing_media_filename}'",
                    )
                self.console.rule("[white on purple]END QUEUE ITEM PROCESSING")

    def start(self):
        self.console.log("Here we go...")
        self.queue = q.Queue()
        self.queue_thread = threading.Thread(target=self.messageQueueLoop, daemon=True)

        self.queue_thread.start()
        self.frontend.start()


def __main__():
    ircawp = Ircawp(config)
    ircawp.start()
