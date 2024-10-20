from datetime import datetime
from typing import Sequence
from .Ircawp_Backend import Ircawp_Backend, InfResponse
from ollama import Client, Message
from app.lib.config import config


class Ollama(Ircawp_Backend):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not config["llm"]["model"]:
            raise ValueError("No model specified in config")

        if not config["llm"]["api_endpoint"]:
            raise ValueError("No API endpoint specified in config")

        self.config = config
        self.model = config["llm"]["model"]
        self.api_endpoint = config["llm"]["api_endpoint"]
        self.ollama = Client(host=self.api_endpoint)

        self.console.log(f"Using model: {self.model}")

    def runInference(
        self,
        prompt: str,
        system_prompt: str | None = None,
        username: str = "",
    ) -> str:
        response = ""

        try:
            if system_prompt == None:
                system_prompt = self.config["llm"].get("system_prompt", None)

            if system_prompt:
                system_prompt = self.templateReplace(
                    system_prompt, username=username
                )

            prompt = prompt.strip()

            tick = datetime.now()

            messages: Sequence[Message] = []

            if system_prompt:
                messages = [
                    {
                        "role": "system",
                        "content": system_prompt,
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ]
            else:
                messages = [
                    {
                        # NOTE: pulling system from user_prompt is intentional
                        "role": "user",
                        "content": prompt,
                    },
                ]

            response = self.ollama.chat(
                model=self.model,
                messages=messages,
                options=self.config.get("options", {}),
                keep_alive=0,
            )

            tok = datetime.now()

            self.last_query_time = tok - tick

            response = response["message"]["content"].strip()

            # compress multiple newlines down to one
            response = "\n".join(
                [line for line in response.split("\n") if line.strip() != ""]
            )

            if len(response) == 0:
                response = "Response was empty. :("

        except RuntimeError as e:
            response = f"**IT HERTZ, IT HERTZ:** '{str(e)}'"

        return response.replace("\n", "\n\n")
