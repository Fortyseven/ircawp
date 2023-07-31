import json
from llama_cpp import Llama
from backends.BaseBackend import BaseBackend
from backends.llamacpp.functions import FUNCTIONS
import datetime

# load model array from models.json
MODELS = None

with open("models.json", "r") as f:
    MODELS = json.load(f)

LLM_MAX_TOKENS = 2048
LLM_TEMP = 0.7
LLM_TOP_P = 0


class LlamaCppBackend(BaseBackend):
    generator = None

    def __init__(self, model="default") -> None:
        self.model = model

    def query(self, user_query: str, raw: bool = False) -> str:
        today = datetime.datetime.now().strftime("%A, %B %d, %Y")

        PROMPT = """
            You are a pleasant AI assistant. You will give full, detailed, helpful answers. The current date is {}.
        """.format(
            today
        ).strip()

        response = ""
        generator = None

        try:
            if user_query.startswith("/"):
                for func in FUNCTIONS:
                    if user_query.startswith("/" + func["name"]):
                        # strips everything before the first space
                        return func["executor"]().execute(
                            user_query[user_query.find(" ") :].strip(), self
                        )
                return "Unknown command. Try `/help`."

            # no function call, basic query
            if raw:
                full_prompt = f"{user_query}"
            else:
                full_prompt = f"{PROMPT}\n\nUser: {user_query}\nAssistant:"

            model = MODELS[self.model]["path"]

            n_ctx = (
                len(full_prompt)
                if len(full_prompt) < LLM_MAX_TOKENS
                else LLM_MAX_TOKENS
            )

            generator = Llama(model_path=model, verbose=True, n_ctx=n_ctx)

            text = generator.create_completion(
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
