"""
Pulls an HTML page and provides a summary
"""

from app.lib.network import fetchHtml
from app.backends.Ircawp_Backend import Ircawp_Backend
from app.media_backends.MediaBackend import MediaBackend
from .__PluginBase import PluginBase
from app.lib.args import parse_arguments, help_arguments

DISCLAIMER = """IMPORTANT: Do NOT include opinion, interpretations, or infer additional context where it does not exist in the provided text, provided media, or your subsequent summary. Only use the information provided in the text. Do not invent information. Strive for accuracy using ONLY the information provided. This is true for the summary, or for follow-up questions asked by the user about the text: only use what is provided."""

SYSTEM_PROMPT = f"""
Summarize the following text. Provide a brief summary of the text. Return only the summary text, without any additional commentary. Ensure the summary is interesting and includes the main points and key details, and is concise and to the point.
{DISCLAIMER}
"""

SYSTEM_PROMPT_FULL = f"""
Summarize the following text. Provide a brief summary of the text, including the main points and key details. The summary should be concise and to the point.

After the summary, provide a short list of bullet points highlighting the overall key details.

Also note any unusual, worrying, or unethical content.

Write the summary taking advantage of Markdown formatting.

{DISCLAIMER}
"""

SYSTEM_PROMPT_EI5 = """
Summarize the following text in a way that a 5-year-old would understand. Use simple language and concepts that a young child can grasp. It should be brief and easy to understand.
"""

SYSTEM_PROMPT_ROAST = """
Summarize the following text in a acidic, sarcastic manner, poking fun at the content. Highlight the flaws, inaccuracies, or logical fallacies in the text. The summary should be witty, cynical, and entertaining, while still capturing the main points of the text. Return only the summary text, without any additional commentary. Keep it at most 2 paragraphs.
"""

DISABLE_IMAGEGEN = True


ARG_SPECS = {
    "roast": {
        "names": ["--roast"],
        "description": "Roast the content in a sarcastic manner",
        "type": bool,
    },
    "full": {
        "names": ["--full"],
        "description": "Provide a detailed summary with key points",
        "type": bool,
    },
    "ei5": {
        "names": ["--ei5"],
        "description": "Summarize in a way a 5-year-old would understand",
        "type": bool,
    },
    "help": {
        "names": ["--help", "-h"],
        "description": "Show this help message",
        "type": bool,
    },
}


def summarize(
    prompt: str,
    media: list,
    backend: Ircawp_Backend,
    media_backend: MediaBackend = None,
) -> tuple[str, str, bool]:
    prompt, config = parse_arguments(prompt, ARG_SPECS)
    print("Parsed config:", config)
    print("Cleaned prompt:", prompt)

    sprompt = SYSTEM_PROMPT

    if config.get("help"):
        return help_arguments(ARG_SPECS), "", False, {}
    elif config.get("roast"):
        sprompt = SYSTEM_PROMPT_ROAST
        # skip_imagegen = False
    elif config.get("full"):
        sprompt = SYSTEM_PROMPT_FULL
    elif config.get("ei5"):
        sprompt = SYSTEM_PROMPT_EI5

    url = prompt.strip().lstrip("<").rstrip(">")
    # Handle URLs with optional pipe and label, e.g., <http://fudge.com|fudge.com>
    if "|" in url:
        url = url.split("|", 1)[0]

    # validate proper url, allow no protocol for plain hostname
    if not (url.startswith("http://") or url.startswith("https://") or "." in url):
        return "Invalid URL provided.", "", True, {}

    # skip_imagegen = True

    text = fetchHtml(url, text_only=True, use_js=True)

    summary, _ = backend.runInference(
        system_prompt=sprompt, prompt=text, use_tools=False
    )

    return summary, "", True, {}


plugin = PluginBase(
    name="Summarize HTML",
    description="Summarizes the given HTML URL.",
    triggers=["summarize", "summary"],
    system_prompt="",
    emoji_prefix="",
    msg_empty_query="No prompt provided",
    msg_exception_prefix="SUMMARIZING PROBLEMS",
    main=summarize,
    use_imagegen=True,
    prompt_required=True,
)
