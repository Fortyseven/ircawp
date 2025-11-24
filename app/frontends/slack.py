import re
import os
import uuid
import dotenv
import requests
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
        self.bolt.event("app_mention")(self.ingestEvent)

        self.console.log("Slack frontend starting.")

        SocketModeHandler(self.bolt, self.slack_creds["SLACK_APP_TOKEN"]).start()

    # @bolt.event("app_mention")
    def ingestEvent(self, event, message, client, say, body):
        self.console.log(
            f"[yellow]:alert: :smile: Ingesting Slack event: {event}[/yellow]"
        )
        user_id = event["user"]
        channel = event["channel"]

        regex = r"(<.*> )(.*)"

        prompt: re.Match | None = re.match(regex, event["text"], re.MULTILINE)

        if prompt:
            prompt = prompt[2]

        username = self.bolt.client.users_info(user=user_id)["user"]["profile"][
            "display_name"
        ]

        incoming_media = []

        # get save user-provided media if present
        if "files" in event:
            # take first file
            file_info = event["files"][0]
            file_url = file_info["url_private_download"]
            try:
                resp = requests.get(
                    file_url,
                    headers={
                        "Authorization": f"Bearer {self.slack_creds['SLACK_BOT_TOKEN']}"
                    },
                    timeout=30,
                )
                resp.raise_for_status()
                media_content = resp.content
            except Exception as e:
                self.console.log(f"[red]Failed to download media: {e}[/red]")
                media_content = b""
            # dump to /tmp with uuid prefix to avoid collisions
            safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", file_info["name"])
            media_path = os.path.join("/tmp", f"{uuid.uuid4()}_{safe_name}")
            with open(media_path, "wb") as f:
                f.write(media_content)
            self.console.log(f"[blue]Saved media temp file: {media_path}[/blue]")
            incoming_media.append(media_path)

        self.parent.ingestMessage(
            prompt.strip(), username, incoming_media, (user_id, channel, say, body)
        )

    def egestEvent(self, message, media, aux={}):
        user_id, channel, say, body = aux

        # HACK:
        media = media[0]

        if not media:
            # say(f"<@{user_id}>: {message}")
            say(
                # text=f"<@{user_id}> {message}",
                blocks=[
                    {
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": f"<@{user_id}> {message}"},
                    }
                ],
            )
        else:
            self._postMedia(message, media, aux)
        pass

    def _postMedia(self, message, media, aux):
        user_id, channel, say, body = aux
        if message:
            response_message_with_username = f"<@{user_id}> {message}"
        else:
            response_message_with_username = ""

        say(
            # text=f"<@{user_id}> {message}",
            blocks=[
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": response_message_with_username},
                }
            ],
        )
        with open(media, "rb") as f:
            self.bolt.client.files_upload_v2(
                file=f.read(),
                channel=channel,
                # initial_comment=response_message_with_username,
                # title=f"{imagegen_prompt}",
            )
