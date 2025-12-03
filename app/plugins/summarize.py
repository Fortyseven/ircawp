"""
Pulls an HTML page and provides a summary
"""

from app.lib.network import fetchHtml
from app.backends.Ircawp_Backend import Ircawp_Backend
from app.media_backends.MediaBackend import MediaBackend
from .__PluginBase import PluginBase

DISCLAIMER = """IMPORTANT: Do NOT include opinion, interpretations, or infer additional context where it does not exist in the provided text or your subsequent summary. Only use the information provided in the text. Do not invent information. Strive for accuracy using ONLY the information provided. This is true for the summary, or for follow-up questions asked by the user about the text: only use what is provided."""

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


def summarize(
    prompt: str,
    media: list,
    backend: Ircawp_Backend,
    media_backend: MediaBackend = None,
) -> tuple[str, str, bool]:
    special_mode = None
    import re

    if prompt.startswith("/?"):
        return (
            (
                "Here are the available summarize modes:\n\n"
                "By default the summarize plugin provides a concise summary of the content.\n\n"
                "• `/i`: Image mode - provides the basic summary with an imagegen run.\n"
                "• `/r`: Roast mode - provides a sarcastic summary of the content.\n"
                "• `/f`: Full mode - provides a detailed summary with key points.\n"
                "• `/5`: Explain Like I'm 5 mode - summarizes the content in a way a 5-year-old would understand.\n\n"
                "You can use these modes by adding the corresponding flag at the start of your summarize command, e.g., `/summarize /r <URL>`"
            ),
            "",
            True,
        )

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
        return "Invalid URL provided.", "", True, {}

    skip_imagegen = True

    text = fetchHtml(url, text_only=True, use_js=True)

    sprompt = None

    match special_mode:
        case "r":
            sprompt = SYSTEM_PROMPT_ROAST
            skip_imagegen = False
        case "f":
            sprompt = SYSTEM_PROMPT_FULL
        case "5":
            sprompt = SYSTEM_PROMPT_EI5
        case "i":
            sprompt = SYSTEM_PROMPT
            skip_imagegen = False
        case _:
            sprompt = SYSTEM_PROMPT

    summary = backend.runInference(
        system_prompt=sprompt,
        prompt=text,
    )

    return (summary, "", skip_imagegen, {})


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
