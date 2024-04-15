from typing import Optional
from backends.BaseBackend import BaseBackend


class AskBase:
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
        self.setMain(main)
        pass

    def setMain(self, main):
        self.main = main

    def execute(
        self,
        query: str,
        backend: BaseBackend,
    ) -> tuple[str, str | dict]:
        print("= AskBase execute: ", self, query)

        if not query.strip() and self.prompt_required:
            return self.msg_empty_query, ""
        try:
            response, media = self.main(query, backend)

            return response, (
                ""
                if (not self.use_imagegen and not media)
                else {
                    "prefix": self.imagegen_prefix,
                    "content": response,
                }
            )
        except Exception as e:
            return f"{self.msg_exception_prefix}: " + str(e), ""
