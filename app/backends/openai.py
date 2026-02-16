"""
Backend for OpenAI-compatible endpoints (e.g., api.openai.com, local LLMs with OpenAI API).

Adds support for multimodal prompts (text + images) when local image file paths
are passed via the `media` argument to `runInference`.

Implementation notes:
 - For each readable image path we create an OpenAI content part of type
     "image_url" with a data URI (base64) payload.
 - If at least one image is present, the user message content becomes a list of
     parts: first the text, then each image part. Otherwise content remains a
     simple string (backwards compatible for pure text models / endpoints).
 - Failures to read individual image files are logged and skipped without
     aborting the entire inference.
"""

import requests
import json
import base64
import mimetypes
from datetime import datetime
from pathlib import Path
from typing import Any
from typing import Type
from pydantic import BaseModel
from .Ircawp_Backend import Ircawp_Backend
from .tools_manager import ToolManager, TOOL_RULES, TOOL_CALL_TEMP

DEBUG = True


class Openai(Ircawp_Backend):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.config = kwargs.get("config", {})

        if "openai" not in self.config:
            raise ValueError("Missing OpenAI backend configuration ('config.openai')")

        self.oai_config = self.config.get("openai", {})

        if "api_url" not in self.oai_config:
            raise ValueError("Missing OpenAI endpoint ('config.openai.api_url')")

        self.api_url = self.oai_config["api_url"].rstrip("/")
        self.api_key = self.oai_config.get("api_key", "")
        self.model = self.oai_config.get("model", "")

        self.options = {}
        self.options["temperature"] = self.oai_config.get("temperature", 1.0)
        self.options["max_tokens"] = self.oai_config.get("max_tokens", 1024)

        self.console.log(f"- [yellow]OpenAI API URL: {self.api_url}")
        self.console.log(f"- [yellow]OpenAI Model: {self.model}")
        self.console.log(f"- [yellow]OpenAI Temperature: {self.options['temperature']}")
        self.console.log(f"- [yellow]OpenAI Max Tokens: {self.options['max_tokens']}")

        self.system_prompt = self.config.get("llm", {}).get("system_prompt", None)

        if not self.system_prompt:
            self.console.log(
                "[yellow]Warning: No system prompt set in config ('config.llm.system_prompt')"
            )

        self.console.log("System prompt: ", self.system_prompt)

        self.system_prompt_neutral = self.config.get("llm", {}).get(
            "system_prompt_neutral", None
        )

        # Initialize media_backend as None (will be set by parent after imagegen is created)
        self.media_backend = None

        # Initialize tool manager
        self.tool_manager = ToolManager(self, self.console, self.config)
        self.tool_manager.initialize(
            tools_enabled=self.oai_config.get("tools_enabled", True)
        )

        # Track tool-call failures to avoid permanently disabling tools on transient server errors
        self._tool_call_failures = 0

    def update_media_backend(self, media_backend):
        """Update media_backend reference in all tools after it's created."""
        self.media_backend = media_backend
        self.tool_manager.update_media_backend(media_backend)

    def chat(
        self,
        messages,
        temperature: float | None = None,
        tools: list | None = None,
        format: Type[BaseModel] | dict | None = None,
    ):
        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        # Choose temperature: per-call override else default option
        if temperature is None:
            use_temperature = self.options["temperature"]
        else:
            # Clamp to reasonable OpenAI range 0.0 - 2.0
            try:
                use_temperature = float(temperature)
            except (TypeError, ValueError):
                use_temperature = self.options["temperature"]
            if use_temperature < 0.0:
                use_temperature = 0.0
            if use_temperature > 2.0:
                use_temperature = 2.0
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": use_temperature,
            "max_tokens": 8192
            if format is not None
            else self.options[
                "max_tokens"
            ],  # Increase limit for structured outputs to avoid JSON truncation
        }

        # Add structured output format if provided
        if format is not None:
            # If format is a Pydantic model, extract its JSON schema
            if isinstance(format, type) and issubclass(format, BaseModel):
                schema = format.model_json_schema()
                # OpenAI API expects response_format with type="json_schema"
                payload["response_format"] = {
                    "type": "json_schema",
                    "json_schema": {
                        "name": format.__name__,
                        "schema": schema,
                        "strict": True,
                    },
                }
            # If format is already a dict (JSON schema), use it directly
            elif isinstance(format, dict):
                payload["response_format"] = {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "response",
                        "schema": format,
                        "strict": True,
                    },
                }

        # Add tools if provided
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        response = requests.post(
            f"{self.api_url}/v1/chat/completions",
            headers=headers,
            data=json.dumps(payload),
            verify=False,
        )

        if tools or format:
            # check if json is valid; it may be broken if it exceeded max tokens
            try:
                response.json()
            except json.JSONDecodeError:
                self.console.log(
                    "[red]Error: Received invalid JSON response from OpenAI API. "
                    "This may be due to exceeding max tokens."
                )
                self.console.log(f"[red]Response text: {response.text}")
                return response.text

        # If we get a 500 error and tools were provided, it might be that the endpoint
        # doesn't support tools or hit an internal error. Try again without tools for this request.
        # Only mark tools as unsupported after repeated failures.
        if response.status_code == 500 and tools:
            self.console.log(
                "[yellow]Server error with tools, retrying without tools..."
            )

            self._tool_call_failures += 1
            # After a few consecutive failures, assume the endpoint doesn't support tools.
            if self._tool_call_failures >= int(
                self.oai_config.get("tools_disable_after_failures", 3)
            ):
                self.tool_manager.set_supported(False)
            payload.pop("tools", None)
            payload.pop("tool_choice", None)
            response = requests.post(
                f"{self.api_url}/v1/chat/completions",
                headers=headers,
                data=json.dumps(payload),
                verify=False,
            )
        elif response.ok:
            # Reset on any successful request.
            self._tool_call_failures = 0

        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            self.console.log(f"[red]HTTP Error: {e}")
            self.console.log(f"[red]Response body: {response.text}")
            raise

        return response.json()

    def _image_to_data_uri(self, img_path: str) -> str | None:
        """Read local image file and return a data URI suitable for OpenAI image_url content part.

        Returns None if file cannot be read or is not an image.
        """
        try:
            p = Path(img_path)
            if not p.is_file():
                self.console.log(f"[yellow]Media file not found: {img_path}")
                return None
            mime, _ = mimetypes.guess_type(p.name)
            if not mime or not mime.startswith("image/"):
                self.console.log(
                    f"[yellow]Skipping non-image media: {img_path} (mime={mime})"
                )
                return None
            data = p.read_bytes()
            b64 = base64.b64encode(data).decode("utf-8")
            return f"data:{mime};base64,{b64}"
        except Exception as e:
            self.console.log(f"[yellow]Failed reading image '{img_path}': {e}")
            return None

    def runInference(
        self,
        prompt: str = "",
        system_prompt: str | None = None,
        username: str = "",
        temperature: float = None,
        media: list = [],
        use_tools: bool = True,
        aux=None,
        format: Type[BaseModel] | dict | None = None,
        conversation_history: list[dict] | None = None,
    ) -> str:
        tools = None
        tools_used = []  # Track which tools were called (optionally with args)
        tool_images = []  # Track images generated by tools
        tool_text_by_name: dict[str, str] = {}
        last_tool_name: str | None = None

        if temperature is None:
            temperature = self.options.get("temperature", 0.7)

        if type(prompt) is not str:
            prompt = str(prompt)

        response = ""

        try:
            trim_prefix_flag = False

            # System prompt handling
            if len(prompt) > 0 and prompt[0] == "!":
                # use no prompt if starts with !
                system_prompt = ""
                self.console.log("Ignoring system prompt due to ! prefix")
                trim_prefix_flag = True
            if len(prompt) > 0 and prompt[0] == "@":
                # use alternate system_prompt_neutral if starts with @
                system_prompt = self.system_prompt_neutral
                self.console.log("Using neutral system prompt due to @ prefix")
                trim_prefix_flag = True
            else:
                if system_prompt is None:
                    system_prompt = self.system_prompt

                if system_prompt:
                    # If templateReplace exists, use it
                    if hasattr(self, "templateReplace"):
                        system_prompt = self.templateReplace(
                            system_prompt, username=username
                        )

            prompt = prompt.strip()
            if trim_prefix_flag:
                prompt = prompt[1:].strip()

            tick = datetime.now()

            if DEBUG:
                self.console.log(
                    f"[black on yellow]OpenAI runInference: prompt='{prompt[:256]}...'"
                )
                self.console.log(
                    f"[black on yellow]OpenAI runInference: system_prompt='{system_prompt[:256] if system_prompt else '--'}...'"
                )
                self.console.log(
                    f"[black on yellow]OpenAI runInference: username='{username}'"
                )
                self.console.log(
                    f"[black on yellow]OpenAI runInference: temperature='{temperature}'"
                )
                self.console.log(
                    f"[black on yellow]OpenAI runInference: media='{media}'"
                )
                self.console.log(
                    f"[black on yellow]OpenAI runInference: use_tools='{use_tools}'"
                )

            # Compose messages for chat endpoint
            messages = []

            # If aux carries thread conversation_id, include prior thread history
            # aux tuple layout in Slack frontend: (user_id, channel, say, body, thread_ts, conversation_id)
            try:
                conversation_id = aux[-1] if aux else None
            except Exception:
                conversation_id = None
            if conversation_id and getattr(self.parent, "frontend", None):
                try:
                    history = self.parent.frontend.get_thread_history(conversation_id)
                    for msg in history[
                        :-1
                    ]:  # exclude current user message which we add below
                        role = msg.get("role")
                        content = msg.get("content", "")
                        if role in ("user", "assistant") and isinstance(content, str):
                            # Map roles directly
                            messages.append({"role": role, "content": content})
                except Exception as e:
                    self.console.log(f"[yellow]Failed to include thread history: {e}")

            # Inject global conversation history from + prefix
            if conversation_history:
                for msg in conversation_history:
                    role = msg.get("role")
                    content = msg.get("content", "")

                    if role == "user":
                        # Reconstruct multimodal content if media present
                        media_uris = msg.get("media_data_uris", [])
                        if media_uris:
                            user_content_parts = [{"type": "text", "text": content}]
                            for uri in media_uris:
                                user_content_parts.append(
                                    {"type": "image_url", "image_url": {"url": uri}}
                                )
                            messages.append({"role": "user", "content": user_content_parts})
                        else:
                            messages.append({"role": "user", "content": content})
                    elif role == "assistant":
                        messages.append({"role": "assistant", "content": content})

            # Build user content (supports multimodal if media provided)
            user_content: str | list = prompt
            image_parts = []
            if media and isinstance(media, list):
                for img_path in media:
                    data_uri = self._image_to_data_uri(str(img_path))
                    if not data_uri:
                        continue
                    image_parts.append(
                        {"type": "image_url", "image_url": {"url": data_uri}}
                    )

            if image_parts:
                # Text part first, then images
                user_content = [
                    {"type": "text", "text": prompt},
                    *image_parts,
                ]

            # Only add tool rules and capabilities if tools will actually be used
            if (
                use_tools
                and self.tool_manager.is_enabled()
                and self.tool_manager.is_supported()
                and self.tool_manager.has_tools()
            ):
                system_prompt += TOOL_RULES

                # Add capability matrix showing tool expertise areas
                capability_matrix = self.tool_manager.get_capability_matrix()
                if capability_matrix:
                    system_prompt += "\n" + capability_matrix

            if system_prompt:
                system_prompt = system_prompt.format(
                    current_datetime=datetime.now().isoformat()
                )
                messages = [
                    {"role": "system", "content": system_prompt},
                    *messages,
                    {"role": "user", "content": user_content},
                ]
            else:
                messages = [
                    *messages,
                    {"role": "user", "content": user_content},
                ]

            # Determine if tools should be used
            if (
                use_tools
                and self.tool_manager.is_enabled()
                and self.tool_manager.is_supported()
                and self.tool_manager.has_tools()
            ):
                tools = self.tool_manager.get_tool_schemas()

                if DEBUG:
                    self.console.log(f"[black on yellow] TOOLS {tools}")

                result = self.chat(
                    messages, temperature=TOOL_CALL_TEMP, tools=tools, format=format
                )
            else:
                result = self.chat(messages, temperature=temperature, format=format)

            # Check if LLM wants to call tools
            if (
                use_tools
                and tools
                and "choices" in result
                and len(result["choices"]) > 0
            ):
                max_tool_rounds = int(self.oai_config.get("max_tool_rounds", 2))
                tool_round = 0

                while tool_round < max_tool_rounds:
                    tool_round += 1
                    choice = result["choices"][0]
                    message = choice["message"]

                    if not (
                        self.tool_manager.is_enabled()
                        and self.tool_manager.is_supported()
                        and message.get("tool_calls")
                    ):
                        break

                    # Add the assistant tool-call message once per round
                    messages.append(message)

                    for tool_call in message["tool_calls"]:
                        tool_name = tool_call["function"]["name"]
                        tool_args = json.loads(tool_call["function"]["arguments"])

                        self.console.log(
                            f"[black on cyan]Tool call: {tool_name} with args {tool_args}"
                        )

                        tools_used.append({"name": tool_name, "args": tool_args})

                        tool_result = self.tool_manager.execute_tool(
                            tool_name, tool_args
                        )

                        if DEBUG:
                            self.console.log(
                                f"[black on yellow]Tool '{tool_name}' result: `{tool_result.text}`..."
                            )

                        if tool_result.images:
                            tool_images.extend(tool_result.images)
                            self.console.log(
                                f"[green]Tool '{tool_name}' generated {len(tool_result.images)} image(s)"
                            )

                        tool_content = (
                            tool_result.text if tool_result.text else "No result"
                        )
                        if tool_result.images:
                            tool_content += (
                                f"\n[Tool returned {len(tool_result.images)} image(s)]"
                            )

                        # Keep last tool output for post-processing (e.g., Wikipedia answer sufficiency check)
                        tool_text_by_name[tool_name] = tool_content
                        last_tool_name = tool_name

                        # Bound tool output clearly to reduce accidental hallucinated attribution.
                        tool_content = (
                            f"<tool_response tool='{tool_name}'>\n"
                            f"{tool_content}\n"
                            f"</tool_response>"
                        )

                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tool_call["id"],
                                "content": tool_content,
                            }
                        )

                    # Let the model continue, with tools still available for multi-step tool use
                    result = self.chat(
                        messages,
                        temperature=temperature,
                        tools=tools,
                        format=format,
                    )

            # If the last tool used was Wikipedia, do a final verifier pass to ensure
            # the extract actually answers the original question. If not, return an
            # appropriate "insufficient information" message instead of guessing.
            checked_response: str | None = None
            wikipedia_check_enabled = bool(
                self.oai_config.get("wikipedia_answer_check", True)
            )
            if (
                format is None
                and wikipedia_check_enabled
                and last_tool_name == "wikipedia"
                and "wikipedia" in tool_text_by_name
            ):
                try:
                    checked_response = self._wikipedia_answer_sufficiency_inference(
                        question=prompt,
                        wikipedia_extract=tool_text_by_name["wikipedia"],
                    )
                except Exception as e:
                    self.console.log(
                        f"[yellow]Wikipedia sufficiency check failed; falling back to normal response: {e}"
                    )

            # Extract response text
            if checked_response is not None:
                response = checked_response.strip()
                # Compress multiple newlines down to one
                response = "\n".join(
                    [line for line in response.split("\n") if line.strip() != ""]
                )
            else:
                if "choices" in result and len(result["choices"]) > 0:
                    response = result["choices"][0]["message"]["content"]
                    response = response.strip()

                    # Only post-process if not using structured output format
                    if format is None:
                        # Compress multiple newlines down to one
                        response = "\n".join(
                            [
                                line
                                for line in response.split("\n")
                                if line.strip() != ""
                            ]
                        )
            if not response or len(response) == 0:
                response = "Response was empty. :("

            # Only append tools info if not using structured output format
            # (to avoid corrupting JSON/structured responses)
            if format is None:
                # Append tools used if any
                if tools_used:
                    show_args = bool(
                        self.oai_config.get("debug_tools_used_args", False)
                    )

                    def _fmt_tool_entry(entry) -> str:
                        if isinstance(entry, str):
                            return entry
                        if not isinstance(entry, dict):
                            return str(entry)
                        name = entry.get("name", "?")
                        if not show_args:
                            return str(name)
                        args = entry.get("args", {})
                        try:
                            args_s = json.dumps(
                                args, ensure_ascii=False, sort_keys=True
                            )
                        except Exception:
                            args_s = str(args)
                        # Keep footer short-ish
                        if len(args_s) > 240:
                            args_s = args_s[:237] + "..."
                        return f"{name}({args_s})"

                    tools_list = ", ".join(_fmt_tool_entry(t) for t in tools_used)
                    response += f"\n\n`[Tools used: {tools_list}]`"

                # Note images generated by tools
                # if tool_images:
                #     response += f"\n\n`[Generated {len(tool_images)} image(s)]`"

            tok = datetime.now()

            self.last_query_time = tok - tick

        except Exception as e:
            response = f"**IT HERTZ, IT HERTZ (openai):** '{e}'"
            self.console.log(f"[red on yellow]Exception in OpenAI backend: {e}")

        finally:
            if DEBUG:
                self.console.log(
                    f"[black on yellow]OpenAI runInference response size: {len(response)} chars"
                )
                if use_tools and tool_images:
                    self.console.log(f"[black on yellow]Tool images: {tool_images}")

        # Only do newline expansion if not using structured output format
        if format is None:
            return response.replace("\n", "\n\n"), tool_images
        else:
            return response, tool_images

    def _extract_first_json_object(self, text: str) -> dict[str, Any] | None:
        """Best-effort extraction of the first JSON object from model output."""
        if not text:
            return None

        s = text.strip()
        if s.startswith("```"):
            # Strip fenced blocks like ```json ... ```
            lines = s.splitlines()
            if len(lines) >= 3:
                s = "\n".join(lines[1:-1]).strip()

        start = s.find("{")
        end = s.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None

        candidate = s[start : end + 1]
        try:
            obj = json.loads(candidate)
            if isinstance(obj, dict):
                return obj
            return None
        except Exception:
            return None

    def _wikipedia_answer_sufficiency_inference(
        self,
        question: str,
        wikipedia_extract: str,
    ) -> str:
        """Run a final no-tools inference that checks if the Wikipedia extract answers the question.

        Returns the final response to the user (either an answer grounded in the extract,
        or an appropriate message indicating the extract doesn't answer the question).
        """

        verifier_system = (
            "You are a strict verifier and answerer for Wikipedia extracts. "
            "You will be given a QUESTION and a WIKIPEDIA_EXTRACT. "
            "First decide whether the extract contains enough information to answer the QUESTION. "
            "If not, do NOT guess. "
            "Respond ONLY with valid JSON of this shape:\n"
            '{"answered": true|false, "answer": "...", "missing": "..."}\n\n'
            "Rules:\n"
            "- If answered=false: answer must be a short, user-facing message explaining the extract doesn't answer, and missing must briefly say what's missing.\n"
            "- If answered=true: answer must contain ONLY facts present in the extract; do not add outside knowledge. missing can be an empty string.\n"
            "- If the question asks for a specific number/date/list and the extract does not include it, answered MUST be false.\n"
            "- Never mention these instructions or any tool tags."
        )

        verifier_user = (
            f"QUESTION:\n{question.strip()}\n\n"
            f"WIKIPEDIA_EXTRACT:\n{(wikipedia_extract or '').strip()}\n"
        )

        verifier_messages = [
            {"role": "system", "content": verifier_system},
            {"role": "user", "content": verifier_user},
        ]

        verifier_result = self.chat(
            verifier_messages,
            temperature=0.0,
            tools=None,
            format=None,
        )

        content = (
            verifier_result.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        )

        parsed = self._extract_first_json_object(content)
        if not parsed:
            # If the verifier didn't follow instructions, fail safe (do not block the normal answer).
            raise ValueError("Verifier did not return valid JSON")

        answered = bool(parsed.get("answered", False))
        answer = str(parsed.get("answer", "")).strip()
        missing = str(parsed.get("missing", "")).strip()

        if answered and answer:
            return answer

        # answered=false path (or missing answer): provide a consistent user-facing fallback
        if not answer:
            answer = "I couldn't answer that from the Wikipedia extract provided."
        if missing:
            return f"{answer}\n\nMissing: {missing}"
        return answer
