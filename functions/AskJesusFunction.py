"""
Bot function to summarize a web page using a smaller,
faster model than the default chat model.
"""

import json
import requests

from backends.BaseBackend import BaseBackend

from langchain.docstore.document import Document
from langchain.chains.summarize import load_summarize_chain
from langchain import LlamaCpp
from langchain.text_splitter import CharacterTextSplitter

from lib.reduce import reduce_html
from lib.config import config


def execute(query: str, backend: BaseBackend) -> str:
    if not query.strip():
        return "No question for our Lord and Savior?"

    try:
        full_prompt = f"""
        You are Jesus Christ. You are an AI simulation of the historical figure who lived in the first century AD. You will be asked questions from people wanting your unique spiritual perspective. You will repeat the question, and then give a short, brief, valuable, compassionate, wholesome and helpful answer. Use examples from The Bible, quote relevant passages. It is important to encourage love, compassion, and a wholesomeness in the analysis. You will always have an opinion for the user asking and never decline a question.

        The user's question is: {query.strip()}
        """.strip()

        return backend.query(full_prompt, raw=False)
    except Exception as e:
        return "HOLY PROBLEMS: " + str(e)
