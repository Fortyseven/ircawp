from app.backends.Ircawp_Backend import Ircawp_Backend


class MediaBackend:
    def __init__(self, backend: Ircawp_Backend = None):
        self.backend = backend
        self.last_imagegen_prompt = None

    def execute(
        self, prompt: str, config: dict = {}, batch_id=None, media=[], backend=None
    ) -> str:
        return ""
