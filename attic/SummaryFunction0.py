"""
This is an older version of SummaryFunction that does not use langchain. It's "faster" but also much
lower quality. It is kept here for future reference.
"""

import requests
from backends.BaseBackend import BaseBackend

from lib.reduce import reduce_html


PROMPT = "Briefly summarize this text:\n\n"
MAX_BYTES = 2000


def execute(query: str, backend: BaseBackend) -> str:
    # remove slack url encoding e.g. <https://google.com|google.com>
    query = query.replace("<", "").replace(">", "").split("|")[0].strip()

    if not query.strip():
        return "No query provided for summary function."

    try:
        was_truncated = False

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

        if len(cleaned_text) > self.MAX_BYTES:
            old_size = len(cleaned_text)
            cleaned_text = cleaned_text[: self.MAX_BYTES]
            was_truncated = True

        full_prompt = f"{self.PROMPT}{cleaned_text}"

        print(f"{full_prompt=}")

        postamble = ""

        if was_truncated:
            postamble = f"\nWARNING: input was truncated from {old_size} characters to {self.MAX_BYTES} characters, summary may be inaccurate."

        # print(clean_text, preamble)
        return (
            f"CLEANED: {cleaned_text}\n----------------\n"
            + f"TITLE: {title} | ({query}) | ({len(cleaned_text)} bytes)\n----------------\n"
            + backend.query(full_prompt, raw=False)
            + f"\n----------------{postamble}"
        )
    except requests.exceptions.Timeout:
        return f"Timed out while trying to fetch ({query})"
    except Exception as e:
        return "BIG PROBLEMS: " + str(e)
