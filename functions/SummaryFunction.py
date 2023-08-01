"""
Bot function to summarize a web page using a smaller,
faster model than the default chat model.
"""

import requests

from backends.BaseBackend import BaseBackend

from langchain.docstore.document import Document
from langchain.chains.summarize import load_summarize_chain
from langchain import LlamaCpp
from langchain.text_splitter import CharacterTextSplitter

from utils.reduce import reduce_html

from lib.config import config

SUMMARY_MODEL = config["models"][config["functions"]["summary"]["model_id"]]


def execute(query: str, backend: BaseBackend) -> str:
    # remove slack url encoding e.g. <https://google.com|google.com>
    query = query.replace("<", "").replace(">", "").split("|")[0].strip()

    if not query.strip():
        return "No query provided for summary function."

    try:
        # ensure query is a valid URL
        if query.find("://") < 0:
            query = f"https://{query}"

        content = requests.get(
            query,
            timeout=4,
            allow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.140 Safari/537.36 Edge/18.17763"
            },
        )

        if content.status_code >= 400:
            return f"Error: code ({content.status_code}) for ({query})"

        cleaned_text, title = reduce_html(content.text)

        JS_STOPPERS = [
            "enable javascript",
            "turn on javascript",
            "javascript is disabled",
            "javascript is turned off",
            "javascript is required",
        ]

        if any([x in cleaned_text.lower() for x in JS_STOPPERS]):
            return f"This site probably requires JavaScript to be enabled. Ask my owner to make a custom handler for ({query})."

        if len(cleaned_text) == 0:
            return f"Error: no usable text returned for ({query})"

        if len(cleaned_text) < 20:
            return f"Error: text too short for ({query}) == ({len(cleaned_text)} bytes)"

        llm = LlamaCpp(
            model_path=SUMMARY_MODEL,
            temperature=0.3,
            # max_tokens=2048,
            n_ctx=2048,
            verbose=False,
            n_gpu_layers=12,
            n_threads=12,
            n_batch=512,
        )

        text_splitter = CharacterTextSplitter()

        texts = text_splitter.split_text(cleaned_text)

        docs = [Document(page_content=text) for text in texts[:3]]

        summarize_chain = load_summarize_chain(
            llm=llm,
            chain_type="map_reduce",
        )
        return (
            f"TITLE: {title} | ({query}) | ({len(cleaned_text)} bytes)\n----------------\n"
            + summarize_chain.run(docs)
        )
    except requests.exceptions.Timeout:
        return f"Timed out while trying to fetch ({query})"
    except Exception as e:
        return "Big problems: " + str(e)
