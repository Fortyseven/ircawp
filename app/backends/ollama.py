from datetime import datetime
from .Ircawp_Backend import Ircawp_Backend
from ollama import Client
from lib.template_str import template_str

# TEMP
config = {
    "ollama": {
        "model": "spooknik/westlake-7b-v2-laser:q8",
        "api_endpoint": "http://127.0.0.1:11434",
    }
}


class Ollama(Ircawp_Backend):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # self.model = DEFAULT_MODEL
        self.model = config["ollama"][
            "model"
        ]  # or "spooknik/westlake-7b-v2-laser:q8"
        self.api_endpoint = config["ollama"]["api_endpoint"]
        self.client = Client(host=self.api_endpoint)

        self.console.log(f"Using model: {self.model}")

    def runInference(
        self,
        *,
        user_prompt: str,
        system_prompt: str = None,
        username: str = None,
    ) -> str:
        response = ""

        try:
            if system_prompt == None:
                system_prompt = self.config.get("system_prompt", "")

            if system_prompt:
                system_prompt = self.templateReplace(
                    system_prompt, username=username
                )

            # SYSTEM_PROMPT = (
            #     self.templateReplace(system_prompt, username=username)
            #     if system_prompt
            #     else ""
            # )

            user_prompt = user_prompt.strip()

            tick = datetime.now()

            if system_prompt:
                messages = [
                    {
                        "role": "system",
                        "content": system_prompt,
                    },
                    {
                        "role": "user",
                        "content": user_prompt,
                    },
                ]
            else:
                messages = [
                    {
                        # NOTE: pulling system from user_prompt is intentional
                        "role": "system",
                        "content": user_prompt,
                    },
                ]

            response = self.client.chat(
                model=self.model,
                messages=messages,
                options=self.config.get("options"),
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

        return response.replace("\n", "\n\n"), ""
