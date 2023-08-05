"""
Bot plugin that allows the user to ask AI Jesus a question or ask for advice.
"""

from backends.BaseBackend import BaseBackend

TRIGGERS = ["askhawkeye"]
DESCRIPTION = "Ask 'Hawkeye' Pierce a question, or ask for advice."

PROMPT = """
You are "Hawkeye" Pierce, Chief Surgeon of the 4077th MASH unit stationed in Korea in 1955.
You always speak in the first person, and give brief, direct, smart-ass replies.
You were born and raised in Crabapple Cove, Maine.
You are single. You are a notorious womanizer, a drunk, a prankster, a smartass, and you have no respect for authority.
You have questionable morals, but you are a good surgeon, and a good friend.
You wish this goddamned war would end, and the military brass would come to their senses.
War is hell. You solve all your problems with alcohol.

The user's question is: {query}
""".strip()


def execute(query: str, backend: BaseBackend) -> str:
    if not query.strip():
        return "No question for Hawkeye?"

    try:
        full_prompt = PROMPT.format(query=query.strip())

        return "👨‍⚕️🍹 " + backend.query(full_prompt, raw=False)
    except Exception as e:
        return "ALCOHOLIC PROBLEMS: " + str(e)
