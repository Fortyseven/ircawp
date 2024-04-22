from typing import Optional
from app.backends.Ircawp_Backend import Ircawp_Backend


class PluginCharacter:
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
        pass

    def execute(
        self,
        query: str,
        backend: Ircawp_Backend,
    ) -> tuple[str, str | dict]:
        print("STEALTH: PluginCharacter execute: ", query)
        if not query.strip():
            return self.msg_empty_query, ""
        try:
            response, _ = backend.runInference(
                user_prompt=query, system_prompt=self.system_prompt.strip()
            )

            return (
                (self.emoji_prefix + " " + response),
                {"prefix": self.imagegen_prefix, "content": response},
            )
        except Exception as e:
            return f"{self.msg_exception_prefix}: " + str(e), ""
