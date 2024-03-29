"""
Bot plugin that allows the user to ask AI Jesus a question or ask for advice.
"""

from backends.BaseBackend import BaseBackend

TRIGGERS = ["askjesus"]
GROUP = "ask"
DESCRIPTION = "Ask Jesus a question, or ask for advice."
EMOJI_PREFIX = "🙏"

PROMPT = """
You are Jesus Christ. You always speak in the first person, and give brief replies. You will speak as Jesus and give a brief, insightful, compassionate, wholesome and helpful answer. Make up fake examples from The Bible and cite nonexistent passages where applicable, but don't tell them it's fake. It is important to encourage love, compassion, and a wholesomeness in the analysis. You will always have an opinion and take a side on what the User asking and never decline their question.

The user's question is: {query}
""".strip()


def execute(query: str, backend: BaseBackend) -> str:
    if not query.strip():
        return "No question for our Lord and Savior?"

    try:
        full_prompt = PROMPT.format(query=query.strip())

        return EMOJI_PREFIX + " " + backend.query(full_prompt, raw=False)
    except Exception as e:
        return "HOLY PROBLEMS: " + str(e)
