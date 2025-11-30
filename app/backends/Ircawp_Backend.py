from __future__ import annotations
from typing import TYPE_CHECKING, Type
import abc

if TYPE_CHECKING:
    from ircawp import Ircawp
    from pydantic import BaseModel


class Ircawp_Backend:
    def __init__(self, *, console, parent: Ircawp, config: dict):
        self.console = console
        self.parent = parent
        self.config = config
        self.last_query_time = 0

        self.console.log(f"Backend config: {self.config}")

    @abc.abstractmethod
    def start():
        pass

    @abc.abstractmethod
    def runInference(
        self,
        prompt: str,
        system_prompt: str | None = None,
        username: str = "",
        temperature: float = 0.7,
        media: list = [],
        use_tools: bool = True,
        aux=None,
        format: "Type[BaseModel] | dict | None" = None,
    ) -> tuple[str, list[str]]:
        """Run inference and return (response_text, tool_generated_images).

        Args:
            prompt: The user prompt text
            system_prompt: Optional system prompt override
            username: Username for template replacement
            temperature: Sampling temperature (default 0.7)
            media: List of media file paths (e.g., images)
            use_tools: Whether to enable tool calling
            aux: Auxiliary data (e.g., thread context)
            format: Optional Pydantic model or JSON schema for structured outputs
        """
        pass

    def templateReplace(self, prompt: str, username: str) -> str:
        prompt = prompt.replace("{username}", username)
        return prompt
