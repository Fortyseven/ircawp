import os
import threading
import queue as q
import time
import importlib

from rich import console as rich_console
from rich.traceback import install

from app.backends.Ircawp_Backend import InfResponse, Ircawp_Backend
from app.media_backends.__MediaBackend import MediaBackend
from app.media_backends.sdxs import SDXS

import app.plugins as plugins
from app.plugins import PLUGINS

from app.lib.config import config

install(show_locals=True)

BANNER = r"""
[red] __
[orange]|__|_______   ____  _____  __  _  ________
[yellow]|  |\_  __ \_/ ___\ \__  \ \ \/ \/ /\____ \
[green]|  | |  | \/\  \___  / __ \_\     / |  |_) )
[blue]|__| |__|    \___  )(____  / \/\_/  |   __/
[purple]                 \/      \/         |__|[/purple]

-=-=-=-=-=-=-=-=-= BOOTING =-=-=-=-=-=-=-=-
""".rstrip()

# temp config

from app.frontends.Ircawp_Frontend import Ircawp_Frontend
import app.frontends.slack as slack


class Ircawp:
    frontend: Ircawp_Frontend
    backend: Ircawp_Backend
    imagegen: MediaBackend
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
            config=self.config.get("backends", {}).get(backend_id, {}),
        )

        #####

        self.console.log("- [yellow]Setting up image generator[/yellow]")

        self.imagegen = SDXS(self.backend)

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
        Process a message from the queue.

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

    def processMessageText(self, message: str, user_id: str, aux: dict):
        """
        Process a message from the queue.

        Args:
            message (str): _description_
            user_id (str): _description_
            aux (Any): _description_

        Returns:
            InfResponse: _description_
        """
        response = self.backend.runInference(
            user_prompt=message,
            system_prompt=None,
            username=user_id,
        )

        return response

    def messageQueueLoop(self):
        self.console.log("Starting message queue thread...")

        thread_sleep = config.get("thread_sleep", 0.250)
        while True:
            response: str = ""
            media: str = ""

            time.sleep(thread_sleep)
            if not self.queue.empty():
                message, user_id, aux = self.queue.get()

                if message.startswith("/"):
                    plugin_name = message.split(" ")[0][1:]
                    if plugin_name in PLUGINS:
                        response, media = self.processMessagePlugin(
                            plugin_name, message=message, user_id=user_id
                        )
                    else:
                        response = f"Plugin {plugin_name} not found."
                        media = ""
                else:
                    response = self.processMessageText(message, user_id, aux)

                self.console.log(f"media: {media}")

                if os.path.exists(media) or not media:
                    pass
                else:
                    # otherwise pass it as a prompt and save that filename
                    media = self.imagegen.execute(media)

                self.console.log(f"media2: {media}")
                self.egestMessage(response, media, aux)

    def start(self):
        self.console.log("Here we go...")
        self.queue = q.Queue()
        self.queue_thread = threading.Thread(
            target=self.messageQueueLoop, daemon=True
        )

        self.queue_thread.start()
        self.frontend.start()


def __main__():
    ircawp = Ircawp(config)
    ircawp.start()
