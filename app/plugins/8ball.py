"""
Magic 8-Ball Plugin
Returns a random fortune-teller style response to any question.
"""

import random
from app.media_backends.MediaBackend import MediaBackend
from app.backends.Ircawp_Backend import Ircawp_Backend
from .__PluginBase import PluginBase


# Classic Magic 8-Ball responses
RESPONSES = [
    # Positive responses
    "It is certain.",
    "It is decidedly so.",
    "Without a doubt.",
    "Yes, definitely.",
    "You may rely on it.",
    "As I see it, yes.",
    "Most likely.",
    "Outlook good.",
    "Yes.",
    "All signs point to yes.",
    # Non-committal responses
    "Reply hazy, ask again.",
    "Ask again later.",
    "Better not tell you now...",
    "Cannot predict now.",
    "Concentrate and ask again.",
    # Negative responses
    "Don't count on it.",
    "My reply is no.",
    "My sources say no.",
    "Outlook not so good.",
    "Very doubtful.",
    "No.",
    "Negative.",
]


def eightball(
    prompt: str,
    media: list,
    backend: Ircawp_Backend,
    media_backend: MediaBackend = None,
) -> tuple[str, str, bool, dict]:
    """Return a random Magic 8-Ball response."""

    response = random.choice(RESPONSES)

    if prompt.strip():
        return f"🎱 {response}", "", True, {}
    else:
        return "🎱 Ask a question first, then shake the ball!", "", True, {}


plugin = PluginBase(
    name="Magic 8-Ball",
    description="Ask the Magic 8-Ball a yes/no question and receive mystical wisdom.",
    triggers=["8ball", "eightball"],
    system_prompt="",
    emoji_prefix="🎱",
    msg_empty_query="Ask a question first!",
    msg_exception_prefix="8-BALL MALFUNCTION",
    main=eightball,
    use_imagegen=False,
    prompt_required=False,
)
