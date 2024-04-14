from datetime import datetime
from typing import Optional

# from llama_cpp import Llama
from ollama import Client
from backends.BaseBackend import BaseBackend
from lib.config import config
from plugins import PLUGINS
from lib.template_str import template_str

# load model array from models.json
LLM_MAX_TOKENS = 2048


class OllamaBackend(BaseBackend):
    ##################
    def __init__(self) -> None:
        # self.model = DEFAULT_MODEL
        self.model = config["ollama"][
            "model"
        ]  # or "spooknik/westlake-7b-v2-laser:q8"
        self.api_endpoint = config["ollama"]["api_endpoint"]
        self.client = Client(host=self.api_endpoint)

        print(f"Using model: {self.model}")

    ##################
    def process_plugin(self, cmd_query: str) -> str:
        """
        Processes a plugin query, which is a string starting with a slash.
        """
        cmd_key = cmd_query.split(" ")[0].strip()[1:]

        for func in PLUGINS:
            if cmd_key in PLUGINS[func].TRIGGERS:
                cmd_plug = PLUGINS[func]

                query = ""

                if len(cmd_query.split()) > 1:
                    query = cmd_query[cmd_query.find(" ") :].strip()

                # strips everything before the first space
                return cmd_plug.execute(
                    query=query,
                    backend=self,
                )

        return "Unknown command. Try `/help`."

    ##################
    def query(
        self,
        user_prompt: str,
        system_prompt: Optional[str] = config["system_prompt"],
        username: Optional[str] = "User",
        raw: Optional[bool] = False,
    ) -> str:
        self.username = username

        response = ""

        try:
            if user_prompt.startswith("/"):
                return self.process_plugin(user_prompt)

            SYSTEM_PROMPT = (
                template_str(system_prompt, username=username)
                if system_prompt
                else ""
            )

            USER_PROMPT = user_prompt.strip()

            tick = datetime.now()

            if system_prompt:
                messages = [
                    {
                        "role": "system",
                        "content": SYSTEM_PROMPT,
                    },
                    {
                        "role": "user",
                        "content": USER_PROMPT,
                    },
                ]
            else:
                messages = [
                    {
                        # NOTE: pulling system from user_prompt is intentional
                        "role": "system",
                        "content": USER_PROMPT,
                    },
                ]

            # was raw?

            options = {
                "temperature": config.get("temperature", 0.75),
            }

            print(f"Messages: {messages}")
            print(f"Options: {options}")

            response = self.client.chat(
                model=self.model,
                messages=messages,
                options=options,
            )

            tok = datetime.now()

            self.last_query_time = tok - tick

            response = response["message"]["content"].strip()

            # this is petty
            response = response.replace("ChatGPT", "ircawp")

            # compress multiple newlines down to one
            response = "\n".join(
                [line for line in response.split("\n") if line.strip() != ""]
            )

            if len(response) == 0:
                response = "Response was empty. :("

        except RuntimeError as e:
            response = f"**IT HERTZ, IT HERTZ:** '{str(e)}'"

        return response.replace("\n", "\n\n")
