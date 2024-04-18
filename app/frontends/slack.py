import re
import dotenv
from .Ircawp_Frontend import Ircawp_Frontend

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler


class Slack(Ircawp_Frontend):
    bolt = None

    ###############################
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.configure()

    ###############################
    def configure(self):
        self.slack_creds = dotenv.dotenv_values(".env")
        if (
            not self.slack_creds["SLACK_APP_TOKEN"]
            or not self.slack_creds["SLACK_BOT_TOKEN"]
        ):
            raise Exception("Slack credentials incomplete. Check .env file.")

    ###############################
    def start(self):
        self.bolt = App(token=self.slack_creds["SLACK_BOT_TOKEN"])

        # self.bolt.action("app_mention")(self.ingest_event)
        # self.bolt.action("event_callback")(self.ingest_event)
        self.bolt.event("app_mention")(self.ingest_event)

        self.console.log("Slack frontend starting.")

        SocketModeHandler(
            self.bolt, self.slack_creds["SLACK_APP_TOKEN"]
        ).start()

    # @bolt.event("app_mention")
    def ingest_event(self, event, message, client, say, body):
        user_id = event["user"]
        channel = event["channel"]

        regex = r"(<.*> )(.*)"

        prompt = re.match(regex, event["text"], re.MULTILINE)[2]

        self.console.log(f"[red]Received message: {prompt}[/red]")

        username = self.bolt.client.users_info(user=user_id)["user"][
            "profile"
        ]["display_name"]

        self.parent.ingest_message(
            prompt, username, (user_id, channel, say, body)
        )

    def egest_event(self, message, media, aux=None):
        user_id, channel, say, body = aux
        say(f"<@{user_id}>: {message}")
        pass