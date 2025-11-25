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
        user_id = event["user"]
        channel = event["channel"]

        regex = r"(<.*>\w?)(.*)"

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
            blocks = self._build_blocks_with_prefix(f"<@{user_id}> ", message or "")
            say(blocks=blocks)
        else:
            self._postMedia(message, media, aux)
        pass

    def _postMedia(self, message, media, aux):
        user_id, channel, say, body = aux
        if message:
            blocks = self._build_blocks_with_prefix(f"<@{user_id}> ", message)
            say(blocks=blocks)
        with open(media, "rb") as f:
            self.bolt.client.files_upload_v2(
                file=f.read(),
                channel=channel,
                # initial_comment=response_message_with_username,
                # title=f"{imagegen_prompt}",
            )

    def _build_blocks_with_prefix(self, prefix: str, content: str, limit: int = 3000):
        content = (content or "").strip()
        blocks = []
        if not content:
            blocks.append(
                {"type": "section", "text": {"type": "mrkdwn", "text": prefix.strip()}}
            )
            return blocks

        # Split into paragraphs (double newlines or blank-line separated)
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n+", content) if p.strip()]

        def append_block(text):
            blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": text}})

        # Helper: sentence split with fallback slicing
        def sentence_chunks(text, max_len):
            sentences = re.split(r"(?<=[.!?])\s+", text)
            out = []
            current = ""
            for s in sentences:
                if not s:
                    continue
                candidate = (current + (" " if current else "") + s) if current else s
                if len(candidate) <= max_len:
                    current = candidate
                else:
                    if current:
                        out.append(current)
                        current = ""
                    # Sentence itself longer than max_len -> hard slice
                    if len(s) > max_len:
                        slice_start = 0
                        while slice_start < len(s):
                            out.append(s[slice_start : slice_start + max_len])
                            slice_start += max_len
                    else:
                        current = s
            if current:
                out.append(current)
            return out

        # First block has prefix space budget
        first_budget = limit - len(prefix)
        first_text = ""
        while paragraphs and len(first_text) < first_budget:
            para = paragraphs[0]
            needed = len(para) + (2 if first_text else 0)  # add separator if not first
            if len(first_text) + needed <= first_budget:
                paragraphs.pop(0)
                first_text = first_text + ("\n\n" if first_text else "") + para
            else:
                # Split paragraph into sentence chunks to fill remaining space
                remaining_space = (
                    first_budget - len(first_text) - (2 if first_text else 0)
                )
                if remaining_space <= 0:
                    break
                chunks = sentence_chunks(para, remaining_space)
                if chunks:
                    fill = chunks[0]
                    first_text = first_text + ("\n\n" if first_text else "") + fill
                    # Replace paragraph with remainder (rejoin leftover chunks)
                    leftover = " ".join(chunks[1:]).strip()
                    if leftover:
                        paragraphs[0] = leftover
                    else:
                        paragraphs.pop(0)
                else:
                    break

        append_block(prefix + first_text)

        # Subsequent blocks (no prefix)
        for para in paragraphs:
            # Break paragraph into block-sized chunks preferring sentence boundaries
            if len(para) <= limit:
                append_block(para)
            else:
                for chunk in sentence_chunks(para, limit):
                    append_block(chunk)
        return blocks
