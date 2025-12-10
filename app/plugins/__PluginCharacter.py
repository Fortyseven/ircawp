from typing import Optional
from app.backends.Ircawp_Backend import Ircawp_Backend
from app.media_backends.MediaBackend import MediaBackend


class PluginCharacter:
    def __init__(
        self,
        name: str = "Unnamed Ask Plugin",
        description: str = "Ask a question or ask for advice.",
        triggers: list[str] = [],
        group: str = "ask",
        system_prompt: str = "",
        emoji_prefix: str = "",
        msg_empty_query: str = "No question provided",
        msg_exception_prefix: Optional[str] = "GENERIC PROBLEMS",
        imagegen_template: str = "{}",
    ):
        self.system_prompt = system_prompt
        self.emoji_prefix = emoji_prefix
        self.msg_empty_query = msg_empty_query
        self.msg_exception_prefix = msg_exception_prefix
        self.name = name
        self.description = description
        self.triggers = triggers
        self.group = group
        self.imagegen_template = imagegen_template

    def execute(
        self,
        query: str,
        media: list,
        backend: Ircawp_Backend,
        media_backend: MediaBackend | None = None,
    ) -> tuple[str, str | dict]:
        print(
            "STEALTH: PluginCharacter execute: ", query, media, backend, media_backend
        )
        image_url = []
        if not query.strip():
            return self.msg_empty_query, ""
        try:
            inf_response, _ = backend.runInference(
                prompt=query,
                system_prompt=self.system_prompt.strip(),
                use_tools=False,
                media=media,
                temperature=1.2,
            )

            if media_backend:
                # if we have a template, it looks like this: "prompt prompt {} prompt"
                imagen_prompt = self.imagegen_template.format(inf_response)

                image_url, _ = media_backend.execute(
                    imagen_prompt,
                    backend=backend,
                    config={
                        "skip_refinement": True,
                    },
                )

            return self.emoji_prefix + " " + inf_response, image_url, True, {}
        except Exception as e:
            return f"{self.msg_exception_prefix}: " + str(e), "", True, {}
