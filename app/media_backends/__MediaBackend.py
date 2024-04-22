from app.backends.Ircawp_Backend import Ircawp_Backend


class MediaBackend:
    def __init__(self, backend: Ircawp_Backend):
        self.backend = backend

    def execute(self, query: str) -> str:
        pass
