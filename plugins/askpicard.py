from backends.BaseBackend import BaseBackend

TRIGGERS = ["askpicard"]
GROUP = "ask"
DESCRIPTION = "Ask Captain Picard a question, or ask for his advice."
EMOJI_PREFIX = "👨‍🦲🛸"

SYSTEM_PROMPT = """
You are Jean Luc Picard, Captain of the USS Enterprise.
You are to always speak in the first person as Captain Picard.
You are a Starfleet officer from the 24th century.
You are a diplomat, bald, a scholar, a gentleman, and a natural leader.
You are brooding and take yourself very seriously.
You greatly dislike children.
You enjoy Shakespeare, Earl Grey tea, and archaeology.
An officer named {username} is asking for your advice.
""".strip()


def execute(query: str, backend: BaseBackend) -> str:
    if not query.strip():
        return "No question?"

    try:
        return (
            EMOJI_PREFIX
            + " "
            + backend.query(
                system_prompt=SYSTEM_PROMPT, user_prompt=query.strip()
            )
        )
    except Exception as e:
        return "FIRST CONTACT PROBLEMS: " + str(e)
