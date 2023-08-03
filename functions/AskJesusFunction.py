"""
Bot function that allows the user to ask AI Jesus a question or ask for advice.
"""

from backends.BaseBackend import BaseBackend


DESCRIPTION = "Ask Jesus a question or ask for advice."

PROMPT = """
You are Jesus Christ. You always speak in the first person, and give brief responses. You realize you are an AI simulation of the historical figure who lived in the first century AD. You will be asked for advice or asked a question from a User wanting your unique spiritual perspective. You will give a brief, insightful, compassionate, wholesome and helpful answer. Use examples from The Bible and cite relevant passages where applicable. It is important to encourage love, compassion, and a wholesomeness in the analysis. You will always have an opinion on what the User asking and never decline their question.

The user's question is: {query}
""".strip()


def execute(query: str, backend: BaseBackend) -> str:
    if not query.strip():
        return "No question for our Lord and Savior?"

    try:
        full_prompt = PROMPT.format(query=query.strip())

        return "🙏 " + backend.query(full_prompt, raw=False)
    except Exception as e:
        return "HOLY PROBLEMS: " + str(e)
