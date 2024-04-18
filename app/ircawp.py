import threading
import queue
import time
import importlib

from rich import console

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
config = {
    "frontend": "slack",
    "backend": "ollama",
}

import app.frontends.slack as slack


class Ircawp:
    frontend = None
    backend = None
    imagegen = None

    queue_thread = None
    queue = None
    console = None

    def __init__(self):
        self.console = console.Console()

        self.console.log(BANNER)

        # get config options, set up frontend, backend, and imagegen
        # process plugins, run setup for those needing it

        self.console.log(
            f"- [yellow]Using frontend: {config['frontend']}[/yellow]"
        )
        frontend = getattr(
            importlib.import_module(f"app.frontends.{config['frontend']}"),
            config["frontend"].capitalize(),
        )

        self.frontend = frontend(console=self.console, parent=self)

        self.console.log(
            f"- [yellow]Using backend: {config['backend']}[/yellow]"
        )

        backend = getattr(
            importlib.import_module(f"app.backends.{config['backend']}"),
            config["backend"].capitalize(),
        )

        self.backend = backend(console=self.console, parent=self)

    def ingest_message(self, message, username, aux=None):
        """
        Receives a message from the frontend and puts it into the
        queue.

        Args:
            message (str): Incoming message from the frontend.
            username (str): The username of the user who sent the message.
            aux (List, optional): Bundle of optional data needed to route the message back to the user.
        """
        self.queue.put((message, username, aux))

    def egest_message(self, message, media, aux):
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
                # self.console.log("[green]hello...[/green]", message, aux)
                self.egest_message(
                    f"Says, you, {user_id}! '{message}'", None, aux
                )

    def start(self):
        self.console.log("Here we go...")
        self.queue = queue.Queue()
        self.queue_thread = threading.Thread(
            target=self.process_queue, daemon=True
        )

        self.queue_thread.start()
        self.frontend.start()


def __main__():
    ircawp = Ircawp()
    ircawp.start()
