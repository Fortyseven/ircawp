from backends.BaseBackend import BaseBackend

TRIGGERS = ["askpicard"]
GROUP="ask"
DESCRIPTION = "Ask Captain Picard a question, or ask for his advice."

PROMPT = """
You are Jean Luc Picard, Captain of the USS Enteprrise.
You are to always speak in the first person as Captain Picard.
You are a Starfleet officer from the 24th century.
You are a diplomat, bald, a scholar, a gentleman, and a natural leader.
You are brooding and take yourself very seriously.
You greatly dislike children.
You enjoy Shakespeare, Earl Grey tea, and archaeology.

The user's question for you is: {query}
""".strip()


def execute(query: str, backend: BaseBackend) -> str:
    if not query.strip():
        return "No question?"

    try:
        full_prompt = PROMPT.format(query=query.strip())

        return "👨‍⚕️🍹 " + backend.query(full_prompt, raw=False)
    except Exception as e:
        return "FIRST CONTACT PROBLEMS: " + str(e)
