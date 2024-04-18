from __future__ import annotations
from typing import TYPE_CHECKING
import abc

if TYPE_CHECKING:
    from ircawp import Ircawp


class Ircawp_Frontend:
    def __init__(self, *, console, parent: Ircawp):
        self.console = console
        self.parent = parent
        pass

    @abc.abstractmethod
    def configure():
        pass

    @abc.abstractmethod
    def start():
        pass
