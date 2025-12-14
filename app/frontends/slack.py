import re
import os
import sys
import uuid
import dotenv
import requests
from .Ircawp_Frontend import Ircawp_Frontend

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

# from app.lib.thread_history import ThreadManager
from app.lib.network import depipeText


class Slack(Ircawp_Frontend):
    bolt = None

    # FIXME: Currently thread history retention is a NOP; we'll return to
    # this later; we're currently only responding to threads for one-offs
    thread_history = None

    ###############################
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.configure()
        # self.thread_history = ThreadManager()

    ###############################
    def configure(self):
        dotenv_file = self.config.get("creds_file", ".env")

        self.slack_creds = dotenv.dotenv_values(dotenv_file)

        self.console.log(
            "[black on light_salmon3]Loaded Slack creds from:", dotenv_file
        )

        if (
            "SLACK_APP_TOKEN" not in self.slack_creds
            or "SLACK_BOT_TOKEN" not in self.slack_creds
        ):
            self.console.log(
                "[red on light_salmon3]Slack credentials incomplete.", self.slack_creds
            )
            sys.exit(-1)

    ###############################
    def start(self):
        from app.plugins import PLUGINS
        from app.lib.config import config

        self.bolt = App(token=self.slack_creds["SLACK_BOT_TOKEN"])

        # Fetch our bot ID
        self.bot_user_id = self.bolt.client.auth_test()["user_id"]
        self.console.log(f"[black on light_salmon3]Bot user id: {self.bot_user_id}")

        # Register dynamic slash commands for plugins (except blacklisted)
        blacklist = set(config.get("llm", {}).get("plugin_blacklist", []))
        self.console.log(f"[black on light_salmon3]Plugin blacklist: {blacklist}")

        def make_plugin_handler(plugin_name):
            def handler(ack, respond, command):
                ack()
                try:
                    # Get backend instance from parent if available
                    backend_instance = self.parent.backend if self.parent else None
                    media_backend_instance = (
                        self.parent.imagegen if self.parent else None
                    )

                    response, outgoing_media, skip_imagegen, meta = PLUGINS[
                        plugin_name
                    ].execute(
                        query=command["text"],
                        media=[],  # Slash commands don't support file uploads
                        backend=backend_instance,
                        media_backend=media_backend_instance,
                    )

                    # Handle media response
                    if outgoing_media:
                        # Post the text response first if present
                        if response:
                            respond(str(response))
                        # Then upload the media file
                        with open(outgoing_media, "rb") as f:
                            self.bolt.client.files_upload_v2(
                                file=f.read(),
                                channel=command["channel_id"],
                            )
                    else:
                        respond(str(response))

                except Exception as e:
                    self.console.log(f"[red]Plugin error in {plugin_name}: {e}")
                    respond(f"[Plugin error: {e}]")

            return handler

        for plugin_name in PLUGINS:
            if plugin_name in blacklist:
                self.console.log(f"[yellow]Skipping blacklisted plugin: /{plugin_name}")
                continue
            slack_command = f"/{plugin_name}"
            self.console.log(f"[green]Registering Slack command: {slack_command}")
            self.bolt.command(slack_command)(make_plugin_handler(plugin_name))

        self.bolt.event("message")(self.ingestEvent)
        SocketModeHandler(self.bolt, self.slack_creds["SLACK_APP_TOKEN"]).start()

    def ingestEvent(self, event, message, client, say, body):
        # Safely extract the user id. Some message subtypes (e.g. message_changed) nest the user.
        user_id = event.get("user")

        if not user_id and isinstance(event.get("message"), dict):
            user_id = event["message"].get("user")

        # If still no user_id, ignore this event.
        if not user_id:
            return

        channel = event["channel"]

        # print("EVENT RECEIVED: ", event)

        # Skip bot's own messages
        if event.get("bot_id") or event.get("subtype") == "bot_message":
            return

        # Get thread_ts - ONLY if user's message was in a thread
        # This allows threads to be optional - user-initiated only
        thread_ts = event.get("thread_ts")  # None if not in a thread

        # conversation_id is only set for actual threads
        # Channel messages have no conversation_id = no history = fresh start
        conversation_id = thread_ts  # None for channel messages

        # For channel messages: only respond if bot is mentioned
        # For thread replies: respond regardless of mention (now that event subscriptions are enabled)
        text = event.get("text", "")

        # TODO: add this to the config
        mention_anywhere = False

        # Only treat as mentioned if OUR bot user id is explicitly present.
        # self.bot_user_id is initialized in start() via auth_test.
        if mention_anywhere:
            mentioned = f"<@{self.bot_user_id}>" in text if self.bot_user_id else False
        else:
            # Only consider as mentioned if at start of message
            regex = rf"^(<@{self.bot_user_id}>)(.*)"
            match = re.match(regex, text, re.MULTILINE)
            mentioned = bool(match)

        # if not thread_ts and not mentioned:
        #     return
        if not mentioned:
            return

        # Extract the prompt text
        # If @mentioned, strip the mention; otherwise use full text (for thread replies)
        if mentioned:
            # Strip ONLY our bot mention prefix to form the prompt.
            regex = rf"(<@{self.bot_user_id}>)(.*)"
            match = re.match(regex, text, re.MULTILINE)
            if match:
                prompt = match[2].strip()
            else:
                # Fallback: remove first occurrence of bot mention anywhere.
                prompt = re.sub(rf"<@{self.bot_user_id}>", "", text).strip()
        else:
            prompt = text.strip()

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
                self.console.log(f"[red on light_salmon3]Failed to download media: {e}")
                media_content = b""
            # dump to /tmp with uuid prefix to avoid collisions
            safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", file_info["name"])
            media_path = os.path.join("/tmp", f"{uuid.uuid4()}_{safe_name}")
            with open(media_path, "wb") as f:
                f.write(media_content)
            self.console.log(
                f"[blue on light_salmon3]Saved media temp file: {media_path}"
            )
            incoming_media.append(media_path)

        # Only store history if in a thread (conversation_id is not None)
        # Channel messages are fresh starts with no history
        # if conversation_id:
        # self.thread_history.addToThreadHistory(conversation_id, "user", prompt)

        self.parent.ingestMessage(
            depipeText(prompt),
            username,
            incoming_media,
            # self.thread_history.getThreadHistory(conversation_id),
            "",
            (
                user_id,
                channel,
                say,
                body,
                thread_ts,
                conversation_id,
            ),
        )

    def egestEvent(self, message, media, aux={}):
        user_id, channel, say, body, thread_ts, conversation_id = aux

        # Only store assistant response if in a thread (conversation_id is not None)
        # Channel messages don't maintain history
        # if conversation_id and message:
        # self.thread_history.addToThreadHistory(
        #     conversation_id, "assistant", str(message)
        # )

        # HACK:
        media = media[0]

        if not media:
            blocks = self._build_blocks_with_prefix(f"<@{user_id}> ", message or "")

            # Only reply in thread if thread_ts exists (user initiated thread)
            if thread_ts:
                say(blocks=blocks, thread_ts=thread_ts)
            else:
                say(blocks=blocks)  # Post to channel, not in thread
        else:
            self._postMedia(message, media, aux)
        pass

    def _postMedia(self, message, media, aux):
        user_id, channel, say, body, thread_ts, conversation_id = aux

        if message:
            blocks = self._build_blocks_with_prefix(f"<@{user_id}> ", message)
            if thread_ts:
                say(blocks=blocks, thread_ts=thread_ts)
            else:
                say(blocks=blocks)

        with open(media, "rb") as f:
            upload_kwargs = {
                "file": f.read(),
                "channel": channel,
                # "initial_comment": "Initial comment.",
                # title=f"{imagegen_prompt}",
            }

            if thread_ts:
                upload_kwargs["thread_ts"] = thread_ts
            self.bolt.client.files_upload_v2(**upload_kwargs)

    def _build_blocks_with_prefix(self, prefix: str, content, limit: int = 3000):
        # Normalize content into a single string. Some plugins/backends may
        # accidentally return a tuple/list (e.g., (text, metadata)). We only
        # want the textual parts for Slack rendering.
        if isinstance(content, (tuple, list)):
            # Flatten one level and join stringifiable, non-empty parts.
            flat_parts = []

            for part in content:
                if part is None:
                    continue

                # If a dict was passed (e.g. metadata), ignore it; but if it
                # has a 'content' key use that.
                if isinstance(part, dict):
                    if "content" in part and isinstance(part["content"], str):
                        flat_parts.append(part["content"])
                    continue

                # Basic stringification; avoid Python tuple/list repr noise by stripping.
                text_part = str(part).strip()
                if text_part:
                    flat_parts.append(text_part)

            content = " \n".join(flat_parts)
        elif not isinstance(content, str):
            content = str(content or "")

        content = (content or "").strip()

        blocks = []

        if not content:
            blocks.append(
                {"type": "section", "text": {"type": "mrkdwn", "text": prefix.strip()}}
            )
            return blocks

        # Split into paragraphs (double newlines or blank-line separated)
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n+", content) if p.strip()]

        def _append_block(text):
            # print("Appending block:", text)
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

        _append_block(prefix + first_text)

        # Subsequent blocks (no prefix)
        for para in paragraphs:
            # Break paragraph into block-sized chunks preferring sentence boundaries
            if len(para) <= limit:
                _append_block(para)
            else:
                for chunk in sentence_chunks(para, limit):
                    _append_block(chunk)
        return blocks
