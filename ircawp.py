import transformers
# from transformers import GPT2LMHeadModel, GPT2Tokenizer, GPTJPreTrainedModel, GPTJModel  # , GPTJToke
import sys

import utils


class IrcAwp:
    generator = None

    MAX_LEN = 128
    TEMP = 0.7
    TOP_K = 40
    NUM_BEAMS = 5
    NO_RPT_ENGRAM_SZ = 2

    def __init__(self, model='gpt2-medium', task='text-generation') -> None:
        '''
        Tasks:
         - 'text-generation'
         - 'question-answering'
        Models:
         - 'gpt2'
         - 'gpt2-medium'
         - 'gpt2-xl'
         - 'EleutherAI/gpt-neo-125M'
         - 'EleutherAI/gpt-neo-1.3B'
         - 'EleutherAI/gpt-neo-2.7B'
         - 'EleutherAI/gpt-j-6B'
        '''
        self.generator = transformers.pipeline(
            model=model, task=task
        )

    def query(self, prompt: str) -> str:
        response = ""

        try:
            text = self.generator(
                prompt,
                max_length=self.MAX_LEN,
                temperature=1,
                top_k=self.TOP_K,
                # max_new_tokens=75,
                num_beams=self.NUM_BEAMS,
                no_repeat_ngram_size=self.NO_RPT_ENGRAM_SZ,
                do_sample=True,
                pad_token_id=50256,
                early_stopping=True
            )

            response = utils.cleanup(prompt, text[0]['generated_text'])

            if len(response) == 0:
                response = "**I don't feel so good, sorry.**"

        except RuntimeError as e:
            response = f"**IT HERTZ, IT HERTZ:** '{str(e)}'"

        return response
