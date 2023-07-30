#!/usr/bin/env python3
import re
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import logging
from backends.llamacpp import IrcAwpLlamaCpp
import dotenv

print("=-=-=-=-= BOOTING =-=-=-=-=")
config = dotenv.dotenv_values(".env")

logging.basicConfig(level=logging.ERROR)

ircawp = None


app = App(token=config["SLACK_BOT_TOKEN"])


@app.event("app_mention")
def event_test(event, message, client, say, body):
    user_id = event["user"]
    regex = r"(<.*> )(.*)"

    matches = re.match(regex, event["text"], re.MULTILINE)

    prompt = matches[2]
    print(f"===============================")
    print(f'LLM Prompt >> "{prompt}"')

    response = ircawp.query(prompt)

    print(f'            << "{response}"')
    print(f"===============================")

    say(f"<@{user_id}>: {response}")


if __name__ == "__main__":
    ircawp = IrcAwpLlamaCpp()
    SocketModeHandler(app, config["SLACK_APP_TOKEN"]).start()
