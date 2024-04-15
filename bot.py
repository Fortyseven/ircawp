#!/usr/bin/env python3
import re
import logging
import time
import dotenv
import queue
import threading
from typing import Callable

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from backends import BaseBackend, LlamaCppBackend, OllamaBackend


from imagegen.BaseImageGen import BaseImageGen
from imagegen.SDXS import SDXS
from imagegen import DEFAULT_IMG_OUTPUT

from lib.config import config
from backends import BaseBackend

print(
    r"""
 __
|__|_______   ____  _____  __  _  ________
|  |\_  __ \_/ ___\ \__  \ \ \/ \/ /\____ \
|  | |  | \/\  \___  / __ \_\     / |  |_) )
|__| |__|    \___  )(____  / \/\_/  |   __/
                 \/      \/         |__|
-=-=-=-=-=-=-=-=-= BOOTING =-=-=-=-=-=-=-=-
""".rstrip()
)

# config
slack_creds = dotenv.dotenv_values(".env")
if not slack_creds["SLACK_APP_TOKEN"] or not slack_creds["SLACK_BOT_TOKEN"]:
    raise Exception("Slack credentials incomplete. Check .env file.")

THREAD_SLEEP = config.get("thread_sleep", 0.250)
logging.basicConfig(level=config.get("log_level", "INFO"))

# globals

slack_queue: queue.Queue = queue.Queue()

backend_instance: BaseBackend | None = None
imagegen_instance: BaseImageGen | None = None

bolt = App(token=slack_creds["SLACK_BOT_TOKEN"])


@bolt.event("app_mention")
def ingest_event(event, message, client, say, body):
    user_id = event["user"]
    channel = event["channel"]

    regex = r"(<.*> )(.*)"

    prompt = re.match(regex, event["text"], re.MULTILINE)[2]

    add_to_queue(user_id, channel, prompt, say)


def add_to_queue(user_id: str, channel: str, message: str, say: Callable):
    """
    Add a message to the queue to be sent to Slack.

    Args:
        user_id (str): The user ID of the user who sent the message.
        channel (str): The channel ID of the channel the message was sent in.
        message (_type_): _description_
        say (_type_): _description_
    """
    slack_queue.put((user_id, channel, message, say))


SIMPLIFIER_THRESHOLD = 120
PROMPT_SIMPLIFIER_IMAGEGEN = """
Summarize the content of this text to under 120 characters for use in an image generator prompt. Greatly simplify the concept to it's basics.
"""


def _simplifyPrompt(prompt: str) -> str:
    if len(prompt) < SIMPLIFIER_THRESHOLD or not prompt:
        return prompt.strip()

    print("\n\n!!! Truncating imagegen prompt")

    result, _ = backend_instance.query(
        prompt,
        system_prompt=f"/raw {PROMPT_SIMPLIFIER_IMAGEGEN}\n\n{prompt}",
    )

    print(f"!!! NEW PROMPT: {result}\n\n)")
    return result.strip()


def say_image(
    *,
    response="",
    media_content="",
    media_prefix="",
    username,
    channel,
):
    if response:
        response_message_with_username = f"@{username} {response}"
    else:
        response_message_with_username = ""

    if media_content:
        imagegen_prompt = media_content or response
        imagegen_prompt = _simplifyPrompt(imagegen_prompt)

        "; ".join([media_prefix or "", imagegen_prompt])

    print(f"!!! Imagegen prompt: {imagegen_prompt}")

    imagegen_instance.generateImage(
        imagegen_prompt,
        DEFAULT_IMG_OUTPUT,
    )

    with open(DEFAULT_IMG_OUTPUT, "rb") as f:
        bolt.client.files_upload_v2(
            file=f.read(),
            channel=channel,
            initial_comment=response_message_with_username,
            title=f"{imagegen_prompt}",
        )


def process_queue_entry(user_id, channel, prompt, say):
    logging.info("==========================")
    logging.info(
        f"Processing queue entry for {user_id} with prompt '{prompt}'"
    )

    skip_imagegen = prompt.endswith("@@")

    prompt = prompt.replace("@@", "")
    prompt = prompt.strip()

    print("\n\n>>> Prompt: ", prompt)

    username = bolt.client.users_info(user=user_id)["user"]["profile"][
        "display_name"
    ]

    response, media = backend_instance.query(prompt, username=username)

    logging.info(f"<<< Response: '{response}', '{media}'")
    print(f"<<< Response: '{response}', Med: '{media}'\n\n")

    if not skip_imagegen and response and not media:
        media = {"content": response, "prefix": ""}

    if (
        skip_imagegen
        # or not media
        or (not (media["content"] if isinstance(media, dict) else media))
        or not imagegen_instance
    ):
        # raw text
        say(f"<@{user_id}>: {response}")
    elif isinstance(media, dict):
        # dict media
        say_image(
            response=response,
            media_content=media["content"],
            media_prefix=media["prefix"],
            channel=channel,
            username=username,
        )
    else:
        # flat string media
        say_image(
            response=response,
            media_content=media,
            channel=channel,
            username=username,
        )
    # else:
    #     say_image(
    #         response=response,
    #         media=None,
    #         username=username,
    #         channel=channel,
    #         augment_with_imagegen=skip_imagegen,
    #     )
    # elif media and :
    #     say_image(
    #         response=response,
    #         media=media,
    #         username=username,
    #         channel=channel,
    #     )
    # else:


def process_queue():
    """
    Process the queue of messages to be sent to Slack until
    the heat death of the universe. But pause for a bit
    now and then.
    """
    logging.info("Starting queue processing thread...")

    while True:
        time.sleep(THREAD_SLEEP)
        if not slack_queue.empty():
            process_queue_entry(*slack_queue.get())


if __name__ == "__main__":
    match config.get("backend", "llamacpp"):
        case "llamacpp":
            backend_instance = LlamaCppBackend()
        case "ollama":
            backend_instance = OllamaBackend()

    imagegen_instance = SDXS()

    queue_thread = threading.Thread(target=process_queue, daemon=True)
    queue_thread.start()

    SocketModeHandler(bolt, slack_creds["SLACK_APP_TOKEN"]).start()
