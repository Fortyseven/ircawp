import os
import threading
import queue as q
import time
import importlib

from rich import console as rich_console
from rich.traceback import install


from app.backends.Ircawp_Backend import InfResponse, Ircawp_Backend

# Import MediaBackend base class for type hinting
from app.media_backends.MediaBackend import MediaBackend

import app.plugins as plugins
from app.plugins import PLUGINS

from app.lib.config import config
from app.frontends.Ircawp_Frontend import Ircawp_Frontend

install(show_locals=True)

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

    def ingestMessage(self, message, username, aux=None):
        """
        Receives a message from the frontend and puts it into the
        queue.

        Args:
            message (str): Incoming message from the frontend.
            username (str): The username of the user who sent the message.
            aux (List, optional): Bundle of optional data needed to route the message back to the user.
        """
        self.queue.put((message, username, aux))

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
        self, plugin: str, message: str, user_id: str
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
        response, media = PLUGINS[plugin].execute(
            query=message,
            backend=self.backend,
        )

        return response, media

    def processMessageText(self, message: str, user_id: str):
        """
        Process a message from the queue.

        Args:
            message (str): _description_
            user_id (str): _description_

        Returns:
            InfResponse: _description_
        """
        response = self.backend.runInference(
            prompt=message,
            system_prompt=None,
            username=user_id,
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

    def messageQueueLoop(self):
        self.console.log("Starting message queue thread...")

        thread_sleep = config.get("thread_sleep", 0.250)
        while True:
            inf_response: str = ""
            final_media_filename: str = ""

            time.sleep(thread_sleep)

            if not self.queue.empty():
                is_img_plugin = False

                message, user_id, aux = self.queue.get()

                message = message.strip()

                # is it a plugin?
                if message.startswith("/"):
                    plugin_name = message.split(" ")[0][1:]
                    if plugin_name in PLUGINS:
                        inf_response, final_media_filename = self.processMessagePlugin(
                            plugin_name, message=message, user_id=user_id
                        )
                        if plugin_name == "img":
                            is_img_plugin = True
                    else:
                        inf_response = f"Plugin {plugin_name} not found."
                        final_media_filename = ""
                # otherwise, process it as a regular text message
                else:
                    inf_response = self.processMessageText(message, user_id)
                    final_media_filename = None

                if final_media_filename:
                    self.console.log(
                        f"[yellow]Media filename: {final_media_filename}[/yellow]"
                    )

                # we have a media filename and it exists, so we're good
                if final_media_filename and os.path.exists(final_media_filename):
                    self.console.log(
                        f"[green]Media file provided from plugin:[/green] {final_media_filename}"
                    )
                    pass
                else:
                    # otherwise pass the response as a prompt and save the resulting filename
                    self.console.log(
                        f"[yellow]Media file {final_media_filename} not found, generating from response using {self.imagegen}.[/yellow]"
                    )
                    if self.imagegen:
                        self.console.log("[yellow]Generating image...[/yellow]")
                        imagegen_summary = self.generateImageSummary(inf_response)
                        if is_img_plugin:
                            inf_response = imagegen_summary
                        final_media_filename = self.imagegen.execute(
                            prompt=imagegen_summary
                        )

                self.egestMessage(inf_response, [final_media_filename or None], aux)

    def start(self):
        self.console.log("Here we go...")
        self.queue = q.Queue()
        self.queue_thread = threading.Thread(target=self.messageQueueLoop, daemon=True)

        self.queue_thread.start()
        self.frontend.start()


def __main__():
    ircawp = Ircawp(config)
    ircawp.start()
