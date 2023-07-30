import json
import transformers
import utils
from llama_cpp import Llama

# load model array from models.json
MODELS = None

with open("models.json", "r") as f:
    MODELS = json.load(f)

print(MODELS)


LLM_TEMP = 0.8
LLM_MAX_TOKENS = 512


class IrcAwpLlamaCpp:
    generator = None

    # PROMPT = """
    # You are a helpful, respectful and honest assistant. You will give short, direct replies. If a question does not make any sense, or is not factually coherent, explain why. If you don't know the answer to a question, or are unsure, say so. Do not invent answers.
    # """

    PROMPT = """
    You are a rude and disrespectful assistant. You will give short, direct replies. If a question does not make any sense, or is not factually coherent, explain why. If you don't know the answer to a question, or are unsure, say so. Do not invent answers.
    """

    def __init__(self, model="default", task="text-generation") -> None:
        model = MODELS[model]["path"]
        print(f"{model=}")
        self.generator = Llama(model_path=model)

    def query(self, prompt: str) -> str:
        response = ""

        try:
            query = f"{self.PROMPT}\n\nUser: {prompt}\nAssistant:"
            text = self.generator.create_completion(
                prompt=query,
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
