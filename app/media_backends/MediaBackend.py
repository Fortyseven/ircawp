from app.backends.Ircawp_Backend import Ircawp_Backend


class MediaBackend:
    def __init__(self, backend: Ircawp_Backend = None):
        self.backend = backend
        self.last_imagegen_prompt = None

    def execute(self, query: str, config: dict) -> str:
        return ""
