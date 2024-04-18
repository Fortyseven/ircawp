from .Ircawp_Backend import Ircawp_Backend


class Ollama(Ircawp_Backend):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.console.log("OLLAMA")
        pass

    def start():
        pass
