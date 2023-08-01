#!/usr/bin/env python3
import re
import logging
import time
import dotenv
import queue
import threading
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from backends.llamacpp.backend import LlamaCppBackend

THREAD_SLEEP = 0.25

print("=-=-=-=-= BOOTING =-=-=-=-=")
config = dotenv.dotenv_values(".env")

logging.basicConfig(level=logging.INFO)

slack_queue = queue.Queue()

ircawp = None

bolt = App(token=config["SLACK_BOT_TOKEN"])


def add_to_queue(user_id, message, say):
    slack_queue.put((user_id, message, say))


def process_queue_entry(user_id, prompt, say):
    logging.info("==========================")
    logging.info(f"Processing queue entry for {user_id} with prompt '{prompt}'")

    response = ircawp.query(prompt)

    logging.info(f"Response: '{response}'")

    say(f"<@{user_id}>: {response}")


@bolt.event("app_mention")
def ingest_event(event, message, client, say, body):
    user_id = event["user"]
    regex = r"(<.*> )(.*)"

    prompt = re.match(regex, event["text"], re.MULTILINE)[2]

    add_to_queue(user_id, prompt, say)


def process_queue():
    logging.info("Starting queue processing thread...")

    while True:
        time.sleep(THREAD_SLEEP)
        if not slack_queue.empty():
            process_queue_entry(*slack_queue.get())


if __name__ == "__main__":
    ircawp = LlamaCppBackend()

    queue_thread = threading.Thread(target=process_queue, daemon=True)
    queue_thread.start()

    SocketModeHandler(bolt, config["SLACK_APP_TOKEN"]).start()
