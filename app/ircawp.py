import threading
import queue
import time
import importlib
from app.backends.Ircawp_Backend import InfResponse, Ircawp_Backend
import app.plugins as plugins
from app.lib.config import config

from rich import console
from rich.traceback import install

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

import app.frontends.slack as slack


class Ircawp:
    frontend = None
    backend: Ircawp_Backend = None
    imagegen = None

    queue_thread = None
    queue = None
    console = None

    def __init__(self, config):
        self.console = console.Console()

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
        self.frontend.egest_event(message, media, aux)

    def process_queue(self):
        self.console.log("Starting queue processing thread...")

        thread_sleep = config.get("thread_sleep", 0.250)
        while True:
            time.sleep(thread_sleep)
            if not self.queue.empty():
                message, user_id, aux = self.queue.get()

                if message.startswith("/"):
                    # TODO: process plugins
                    response, media = self.processPlugin(message, user_id)
                else:
                    response, media = self.backend.runInference(
                        user_prompt=message,
                        system_prompt=None,
                        username=user_id,
                    )
                self.egestMessage(response, media, aux)

    def start(self):
        self.console.log("Here we go...")
        self.queue = queue.Queue()
        self.queue_thread = threading.Thread(
            target=self.messageQueueLoop, daemon=True
        )

        self.queue_thread.start()
        self.frontend.start()


def __main__():
    ircawp = Ircawp(config)
    ircawp.start()
