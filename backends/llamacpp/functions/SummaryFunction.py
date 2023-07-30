import requests
from backends.BaseBackend import BaseBackend
from backends.llamacpp.functions import BaseFunction
from bs4 import BeautifulSoup


class SummaryFunction(BaseFunction.BaseFunction):
    PROMPT = "Summarize this content:\n"
    MAX_BYTES = 2000

    def execute(self, query: str, backend: BaseBackend) -> str:
        if not query:
            return "No query provided for summary function"

        # full_prompt = f"{self.PROMPT}\n\nUser: {user_query}\nAssistant:"

        try:
            was_truncated = False

            # ensure query is a valid URL
            if query.find("://") < 0:
                query = f"https://{query}"

            content = requests.get(query, timeout=4, allow_redirects=True, verify=False, )

            if content.status_code >= 400:
                return f"Error: code ({content.status_code}) for ({query})"

            soup = BeautifulSoup(content.text, "html.parser")

            for x in ["noscript", "nav", "script", "svg"]:
                for y in soup.find_all(x):
                    y.decompose()

            # get title

            title = soup.find("title").text.strip()

            clean_text = soup.get_text().strip()

            clean_text = " ".join(clean_text.split())

            JS_STOPPERS = [
                "enable javascript",
                "turn on javascript",
                "javascript is disabled",
                "javascript is turned off",
                "javascript is required",
            ]

            if any([x in clean_text.lower() for x in JS_STOPPERS]):
                return f"This site probably requires JavaScript to be enabled. Ask my owner to make a custom handler for ({query})."

            if len(clean_text) == 0:
                return f"Error: no text returned for ({query})"

            if len(clean_text) < 20:
                return (
                    f"Error: text too short for ({query}) == ({len(clean_text)} bytes)"
                )

            if len(clean_text) > self.MAX_BYTES:
                old_size = len(clean_text)
                clean_text = clean_text[: self.MAX_BYTES]
                was_truncated = True

            full_prompt = f"{self.PROMPT}{clean_text}"

            # TODO:
            # - de-dupe sentences
            # - remove common non-relevant text (e.g. "click here to learn more", "Search", "Sign in", etc.)

            postamble = ""

            if was_truncated:
                postamble = f"\nWARNING: input was truncated from {old_size} characters to {self.MAX_BYTES} characters, summary may be inaccurate."

            # print(clean_text, preamble)
            return (
                f"TITLE: {title} | ({query}) | ({len(clean_text)} bytes)\n----------------\n"
                + backend.query(full_prompt, raw=False)
                + f"\n----------------{postamble}"
            )
        except requests.exceptions.Timeout:
            return f"Timed out while trying to fetch ({query})"
        except Exception as e:
            return "Big problems: " + str(e)
