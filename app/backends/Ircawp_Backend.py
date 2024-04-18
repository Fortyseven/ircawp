from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ircawp import Ircawp


class Ircawp_Backend:
    def __init__(self, *, console, parent: Ircawp):
        self.console = console
        self.parent = parent

    def start():
        pass
