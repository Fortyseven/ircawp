import random
from datetime import datetime
from llama_cpp import Llama
from backends.BaseBackend import BaseBackend
from lib.config import config
from plugins import PLUGINS
from lib.template_str import template_str

# load model array from models.json
LLM_MAX_TOKENS = 2048


class LlamaCppBackend(BaseBackend):
    generator = None

    def __init__(self) -> None:
        self.model = config["models"][config.get("chat_model_id", "default")]

        self.generator = Llama(
            model_path=self.model,
            verbose=False,
            n_ctx=config.get("n_ctx", 1024),
            n_gpu_layers=12,
            n_threads=12,
            n_batch=512,
        )

        print(f"Using model: {self.model}")

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

    def query(
        self, user_query: str, raw: bool = False, username: str = "User"
    ) -> str:
        self.username = username

        response = ""

        try:
            if user_query.startswith("/"):
                return self.process_plugin(user_query)

            PROMPT = template_str(
                config["system_prompt"],
                username=username,
                query=user_query.strip(),
            )

            # no plugin call, basic query
            if raw:
                full_prompt = f"{user_query}"
            else:
                full_prompt = f"{PROMPT}\nircawp: "

            n_ctx = (
                len(full_prompt)
                if len(full_prompt) < LLM_MAX_TOKENS
                else LLM_MAX_TOKENS
            )

            tick = datetime.now()

            # random_seed_number = random.randint(0, 9999999999)
            # print("- SEED: ", random_seed_number)

            text = self.generator.create_completion(
                prompt=full_prompt,
                max_tokens=2048,
                temperature=config.get("temperature", 0.75),
                # seed=random_seed_number,
                # mirostat_mode=True,
                stop=[
                    "User:",
                    f"{username}:",
                    f"{username} asks",
                    f"{username} replies",
                    f"{username} says",
                    f"{username} answers",
                    "``` \n```",
                    "```\n ```",
                ],
                echo=True,
            )

            tok = datetime.now()

            self.last_query_time = tok - tick

            response = text["choices"][0]["text"].strip()
            # response = response[response.find("ircawp:") + 10 :].strip()
            response = response.removeprefix(full_prompt).strip()

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
