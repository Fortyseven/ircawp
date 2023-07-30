import json
from llama_cpp import Llama
from backends.BaseBackend import BaseBackend
from backends.llamacpp.functions import FUNCTIONS

# load model array from models.json
MODELS = None

with open("models.json", "r") as f:
    MODELS = json.load(f)

LLM_MAX_TOKENS = 512
LLM_TEMP = 0.8


class LlamaCppBackend(BaseBackend):
    generator = None

    # PROMPT = """
    # You are a helpful, respectful and honest assistant. You will give short, direct replies. If a question does not make any sense, or is not factually coherent, explain why. If you don't know the answer to a question, or are unsure, say so. Do not invent answers.
    # """

    PROMPT = """
    You are a rude and disrespectful assistant. You will give short, direct replies. If a question does not make any sense, or is not factually coherent, explain why. If you don't know the answer to a question, or are unsure, say so. Do not invent answers.
    """

    def __init__(self, model="default") -> None:
        model = MODELS[model]["path"]
        print(f"{model=}")
        self.generator = Llama(model_path=model, verbose=False, n_ctx=2048)

    def query(self, user_query: str, raw: bool = False) -> str:
        response = ""

        try:
            if user_query.startswith("/"):
                for func in FUNCTIONS:
                    # print(user_query, f"{func=}", func["name"])
                    if user_query.startswith("/" + func["name"]):
                        # print("FUNK", func["name"])
                        # strips everything before the first space
                        # NOTE: this will break multi-word commands, so we should fix this
                        return func["executor"]().execute(
                            user_query[user_query.find(" ") :].strip(), self
                        )
                return "Unknown command. Try `/help`."

            # no function call, basic query

            if raw:
                full_prompt = f"{user_query}"
            else:
                full_prompt = f"{self.PROMPT}\n\nUser: {user_query}\nAssistant:"

            text = self.generator.create_completion(
                prompt=full_prompt,
                max_tokens=LLM_MAX_TOKENS,
                temperature=LLM_TEMP,
                top_p=0.9,
                stop=["User:", "\n\n"],
                echo=True,
            )

            response = text["choices"][0]["text"].strip()
            response = response[response.find("Assistant:") + 10 :].strip()

            if len(response) == 0:
                response = "**I don't feel so good, Mr. Stark.**"

        except RuntimeError as e:
            response = f"**IT HERTZ, IT HERTZ:** '{str(e)}'"

        return response
