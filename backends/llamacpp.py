from llama_cpp import Llama
from backends.BaseBackend import BaseBackend
from lib.config import config
from functions import FUNCTIONS

import datetime

# load model array from models.json
LLM_MAX_TOKENS = 2048
LLM_TEMP = 0.7
LLM_TOP_P = 0


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

    def process_function(self, cmd_query: str) -> str:
        """
        Processes a command query, which is a string starting with a slash.
        """
        cmd_key = cmd_query.split(" ")[0].strip()[1:]

        if not cmd_key in FUNCTIONS:
            return "Unknown command. Try `/help`."

        cmd_func = FUNCTIONS[cmd_key]

        # strips everything before the first space
        return cmd_func["execute"](
            query=cmd_query[cmd_query.find(" ") :].strip(),
            backend=self,
        )

    def query(self, user_query: str, raw: bool = False) -> str:
        today = datetime.datetime.now().strftime("%A, %B %d, %Y")

        PROMPT = """
            You are a pleasant AI assistant. You will give full, detailed, helpful answers. The current date is {}.
        """.format(
            today
        ).strip()

        response = ""

        try:
            if user_query.startswith("/"):
                return self.process_function(user_query)

            # no function call, basic query
            if raw:
                full_prompt = f"{user_query}"
            else:
                full_prompt = f"{PROMPT}\n\nUser: {user_query}\nAssistant:"

            n_ctx = (
                len(full_prompt)
                if len(full_prompt) < LLM_MAX_TOKENS
                else LLM_MAX_TOKENS
            )

            text = self.generator.create_completion(
                prompt=full_prompt,
                max_tokens=2048,
                temperature=LLM_TEMP,
                mirostat_mode=True,
                # top_p=LLM_TOP_P,
                stop=["User:"],
                echo=True,
            )

            response = text["choices"][0]["text"].strip()
            response = response[response.find("Assistant:") + 10 :].strip()

            if len(response) == 0:
                response = "Response was empty. :("

        except RuntimeError as e:
            response = f"**IT HERTZ, IT HERTZ:** '{str(e)}'"

        return response
