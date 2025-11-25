from __future__ import annotations
from typing import TYPE_CHECKING
import abc

from app.types import InfResponse

if TYPE_CHECKING:
    from ircawp import Ircawp


class Ircawp_Backend:
    def __init__(self, *, console, parent: Ircawp, config: dict):
        self.console = console
        self.parent = parent
        self.config = config
        self.last_query_time = 0

        self.console.log(f"Backend config: {self.config}")

    @abc.abstractmethod
    def start():
        pass

    @abc.abstractmethod
    def runInference(
        self,
        prompt: str,
        system_prompt: str | None = None,
        username: str = "",
    ) -> str:
        pass

    def templateReplace(self, prompt: str, username: str) -> str:
        prompt = prompt.replace("{username}", username)
        return prompt
