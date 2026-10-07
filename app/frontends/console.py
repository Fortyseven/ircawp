"""
Console frontend: a REPL that drives the bot exactly like the Slack frontend.

Every line typed in the REPL is fed through the full production pipeline
(message queue, routing, plugins, URL extraction, media) the same way a
Slack message would be, so bot behavior can be tested from the command
line without a Slack workspace.

Slack equivalents:
  plain text         -> channel message (fresh conversation)
  +text              -> thread reply (continues the conversation)
  /plugin args       -> slash command
  ^text              -> uses the most recently generated image
  a valid file path  -> file upload (attachment)
"""

import shutil
import threading
import uuid
from pathlib import Path

from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text

from .Ircawp_Frontend import Ircawp_Frontend


class Console(Ircawp_Frontend):
    """A stdin/stdout frontend for the bot."""

    def configure(self):
        """No external credentials are needed for the console frontend."""
        self.console.log(
            "[black on light_salmon3]Console frontend: no credentials required"
        )

    def ingestEvent(self, event, message, client, say, body):
        # Not used: the REPL ingests directly via parent.ingestMessage.
        pass

    def egestEvent(self, message, media, aux=None):
        """Print the bot's response, then signal the REPL that this turn is done."""
        if not isinstance(message, str):
            message = str(message)
        self.console.print(
            Text.from_markup("[bold blue]ircawp[/bold blue]: ") + Text(message)
        )

        media_file = media[0] if media else None
        if media_file:
            self.console.print(Text(f"media: {media_file}", style="dim"))

        # aux layout: (user_id, channel, say, body, thread_ts, conversation_id, done)
        if aux and isinstance(aux[-1], threading.Event):
            aux[-1].set()

    def start(self):
        """Entry point: one-shot mode if a prompt was given, otherwise the REPL."""
        one_shot = self.config.get("console_prompt")
        if one_shot:
            self._send_and_wait(one_shot)
            self.console.print(Text("[dim]bye[/dim]"))
            return
        self._repl_loop()

    def _repl_loop(self) -> None:
        """Interactive loop: read lines and feed them to the bot."""
        self.console.print(self._welcome_panel())

        while True:
            try:
                line = Prompt.ask("[bold green]❯[/bold green]").strip()
            except (EOFError, KeyboardInterrupt):
                self.console.print("\n[dim]bye[/dim]")
                return

            if not line:
                continue
            if line.lower() in ("q", "quit", "exit"):
                self.console.print("[dim]bye[/dim]")
                return
            if line.lower() in ("help", "?"):
                self.console.print()
                self._print_help()
                continue

            try:
                self._send_and_wait(line)
            except KeyboardInterrupt:
                self.console.print(
                    "\n[yellow]interrupted (the bot will still finish its response)[/yellow]"
                )

    def _send_and_wait(self, line: str) -> None:
        """Send one line through the real bot pipeline and wait for the response."""
        text, media = self._prepare_media(line)

        self.console.print(
            Text.from_markup("[bold green]you[/bold green]: ") + Text(line)
        )
        for path in media:
            self.console.print(Text(f"  attached: {path}", style="dim"))

        done = threading.Event()
        aux = ("CLI", "console", None, None, None, None, done)
        self.parent.ingestMessage(text, "CLI", media, aux)
        done.wait()

    def _prepare_media(self, line: str) -> tuple[str, list[str]]:
        """Split a line into (text, media paths), simulating Slack file uploads.

        Any token that is a valid file path is stripped from the text and
        treated as an attachment. Files are copied into the bot's media dir
        because the router deletes incoming media after processing and the
        user's originals must survive.
        """
        tokens = line.split()
        paths = [t for t in tokens if Path(t).is_file()]
        text = " ".join(t for t in tokens if t not in paths).strip()

        media_dir = Path(self.parent.media_manager.media_dir)
        media = []
        for path in paths:
            dest = media_dir / f"{uuid.uuid4()}_{Path(path).name}"
            shutil.copy2(path, dest)
            media.append(str(dest))

        return text, media

    def _welcome_panel(self) -> Panel:
        """The welcome banner shown when the REPL starts."""
        return Panel.fit(
            "Every line is sent to the bot through the full pipeline,\n"
            "exactly like a Slack message. Type [bold]help[/bold] for the syntax.",
            title="[bold magenta]ircawp chat[/bold magenta]",
            border_style="magenta",
        )

    def _print_help(self) -> None:
        """Print the REPL help table."""
        table = Table(box=None, show_header=False, padding=(0, 2))
        table.add_column(style="bold cyan", no_wrap=True)
        table.add_column()
        table.add_row("text", "fresh conversation (like a channel message)")
        table.add_row("+text", "continue the conversation (like a thread reply)")
        table.add_row("^text", "prepend the last generated image to the message")
        table.add_row("!text", "skip the system prompt (handled by the backend)")
        table.add_row("@text", "neutral system prompt (handled by the backend)")
        table.add_row(
            "/plugin args", "run a plugin (type /help to the bot for the list)"
        )
        table.add_row(
            "<file path>",
            "a valid path in the line is stripped and attached as media"
            " (quote it to send it as text)",
        )
        table.add_row("bare URL", "auto-routed to /yt or /summarize")
        table.add_row("help / ?", "show this help")
        table.add_row("q / quit", "exit (Ctrl+C and Ctrl+D also work)")
        self.console.print(table)
