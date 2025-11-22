"""
Pulls an HTML page and provides a summary
"""

from app.backends.Ircawp_Backend import Ircawp_Backend
from .__PluginBase import PluginBase
import feedparser
from bs4 import BeautifulSoup

SYSTEM_PROMPT = """
Summarize the following text. Provide a brief summary of the text. Return only the summary text, without any additional commentary. Ensure the summary is interesting and includes the main points and key details, and is concise and to the point.
"""

SYSTEM_PROMPT_FULL = """
Summarize the following text. Provide a brief summary of the text, including the main points and key details. The summary should be concise and to the point.

After the summary, provide a short list of bullet points highlighting the overall key details.

Also note any unusual, worrying, or unethical content.

Write the summary taking advantage of Markdown formatting.
"""

SYSTEM_PROMPT_EI5 = """
Summarize the following text in a way that a 5-year-old would understand. Use simple language and concepts that a young child can grasp. It should be brief and easy to understand.
"""


def summarize(prompt: str, backend: Ircawp_Backend) -> tuple[str, str]:
    # prompt will have the URL to summarize in this format: `<https://example.com>`

    # Handle /x flag at start or end of prompt
    special_mode = None
    import re

    match = re.match(r"^/(\w)\s+(.+)$", prompt)
    if match:
        special_mode = match.group(1)
        prompt = match.group(2)
    else:
        match_end = re.match(r"(.+)\s+/([\w])$", prompt)
        if match_end:
            special_mode = match_end.group(2)
            prompt = match_end.group(1)

    url = prompt.strip().lstrip("<").rstrip(">")
    # Handle URLs with optional pipe and label, e.g., <http://fudge.com|fudge.com>
    if "|" in url:
        url = url.split("|", 1)[0]

    # validate proper url, allow no protocol for plain hostname
    if not (url.startswith("http://") or url.startswith("https://") or "." in url):
        return "Invalid URL provided.", ""

    try:
        import requests

        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        return f"Error fetching URL: {e}", ""

    soup = BeautifulSoup(resp.text, "html.parser")
    text = soup.get_text(separator="\n", strip=True)

    match special_mode:
        case "full":
            summary = backend.runInference(
                system_prompt=SYSTEM_PROMPT_FULL,
                prompt=text,
            )
        case "5":
            summary = backend.runInference(
                system_prompt=SYSTEM_PROMPT_EI5,
                prompt=text,
            )
        case _:
            summary = backend.runInference(
                system_prompt=SYSTEM_PROMPT,
                prompt=text,
            )

    return (
        # f"Top stories from Hacker News as of {START_TIME.strftime('%Y-%m-%d %H:%M:%S')}"
        # + "\n".join(
        #     [
        #         f"{i + 1}. {feed.entries[i].title} - {feed.entries[i].link}"
        #         for i in range(5)
        #     ]
        # ),
        # "",
        summary,
        "",
    )


plugin = PluginBase(
    name="Summarize HTML",
    description="Summarizes the given HTML URL.",
    triggers=["summarize"],
    system_prompt="",
    emoji_prefix="",
    msg_empty_query="No prompt provided",
    msg_exception_prefix="SUMMARIZING PROBLEMS",
    main=summarize,
    use_imagegen=True,
    prompt_required=True,
)
