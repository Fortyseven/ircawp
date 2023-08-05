import json
import requests

from backends.BaseBackend import BaseBackend

from langchain.docstore.document import Document
from langchain.chains.summarize import load_summarize_chain
from langchain import LlamaCpp
from langchain.text_splitter import CharacterTextSplitter

from lib.reduce import reduce_html
from lib.config import config

import requests
import bs4 as BeautifulSoup

TRIGGERS = ["wiki"]
DESCRIPTION = "Pull up a stripped down Wikipedia article."
EMOJI_PREFIX = "🌐"


def process_wiki_json(json_text: str) -> str:
    try:
        wiki_data = json.loads(json_text)

        page = wiki_data["query"]["pages"]
        key = list(page.keys())[0]

        title = page[key]["title"]

        if "extract" not in page[key]:
            return f"Error: couldn't find a page for '{title}'."

        extract = page[key]["extract"]

        if "Redirect_template" in extract:
            extract = f"'{title}' is a redirect page."

        # clean html from extract
        soup = BeautifulSoup.BeautifulSoup(extract, "html.parser")
        extract = soup.get_text().replace("\n", "\n\n").strip()
        full_link = f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}"

        return f"{EMOJI_PREFIX} {title}\n\n{extract}\n\n{full_link}"

    except json.decoder.JSONDecodeError:
        return "Error: could not decode JSON."


def execute(query: str, backend: BaseBackend) -> str:
    if not query.strip():
        return "No query provided for wikipedia plugin."

    try:
        url_query = f"https://en.wikipedia.org/w/api.php?action=query&prop=extracts&format=json&exintro=&titles={query}"
        response = requests.get(url_query, timeout=12, allow_redirects=True)

        if response.status_code >= 400:
            return f"Error: code ({response.status_code}) for ({url_query})"

        return process_wiki_json(response.text)
    except requests.exceptions.Timeout:
        return f"Timed out while trying to fetch ({url_query})."
    except Exception as e:
        return "BIG PROBLEMS: " + str(e)
