from typing import Optional
from app.backends.Ircawp_Backend import Ircawp_Backend
from app.media_backends.MediaBackend import MediaBackend


class PluginBase:
    def __init__(
        self,
        name: str = "Unnamed Ask Plugin",
        description: str = "Ask a question or ask for advice.",
        triggers: list[str] = [],
        group: str = "ask",
        system_prompt: str = "",
        emoji_prefix: str = "",
        imagegen_prefix: str | None = None,
        msg_empty_query: str = "No question provided",
        msg_exception_prefix: Optional[str] = "GENERIC PROBLEMS",
        prompt_required: bool = True,
        use_imagegen: bool = False,
        backend: Ircawp_Backend | None = None,
        media_backend: MediaBackend | None = None,
        init=None,
        main=None,
    ):
        self.system_prompt = system_prompt
        self.emoji_prefix = emoji_prefix
        self.imagegen_prefix = imagegen_prefix
        self.msg_empty_query = msg_empty_query
        self.msg_exception_prefix = msg_exception_prefix
        self.name = name
        self.description = description
        self.triggers = triggers
        self.group = group
        self.use_imagegen = use_imagegen
        self.prompt_required = prompt_required
        self.backend: Ircawp_Backend = backend
        self.media_backend: MediaBackend = media_backend
        self.setMain(main)

        if init:
            init(self.backend)

    def setMain(self, main):
        self.main = main

    def execute(
        self,
        query: str,
        media: list,
        backend: Ircawp_Backend,
        media_backend: MediaBackend | None = None,
    ) -> tuple[str, str | dict, bool, dict]:
        backend.console.log("[black on green]= PluginBase execute: ", query, media)

        if not query.strip() and self.prompt_required:
            return self.msg_empty_query, "", True, {}
        try:
            media_return = ""

            response, outgoing_media, skip_imagegen, meta = self.main(
                query, media, backend, media_backend
            )

            if outgoing_media and isinstance(outgoing_media, str):
                media_return = outgoing_media

            return (response, media_return, skip_imagegen, meta)
        except Exception as e:
            return (f"{self.msg_exception_prefix}: {e}", "", True, {})
