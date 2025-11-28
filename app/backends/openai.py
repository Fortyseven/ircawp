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
from .Ircawp_Backend import Ircawp_Backend
from .tools import get_all_tools
from .tools.ToolBase import ToolResult

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

        # Initialize media_backend as None (will be set by parent after imagegen is created)
        self.media_backend = None

        # Initialize tools
        self.tools_enabled = self.oai_config.get("tools_enabled", True)
        self.tools_supported = True  # Track if endpoint supports tools
        self.available_tools = {}
        if self.tools_enabled:
            self._initialize_tools()
        else:
            self.console.log("[yellow]Tools disabled in config")

    def _initialize_tools(self):
        """Initialize and register available tools."""
        all_tools = get_all_tools()
        for tool_name, tool_factory in all_tools.items():
            try:
                # Instantiate tool with access to backend and media backend
                # Works for both class-based and decorator-based tools
                tool_instance = tool_factory(
                    backend=self,
                    media_backend=self.media_backend,
                    console=self.console,
                )
                self.available_tools[tool_name] = tool_instance
                self.console.log(f"- [green]Registered tool: {tool_name}")
            except Exception as e:
                self.console.log(f"[yellow]Failed to initialize tool {tool_name}: {e}")

    def update_media_backend(self, media_backend):
        """Update media_backend reference in all tools after it's created."""
        self.media_backend = media_backend

        # Update media_backend in all existing tool instances
        for tool_name, tool_instance in self.available_tools.items():
            tool_instance.media_backend = media_backend
            self.console.log(f"- [cyan]Updated media_backend for tool: {tool_name}")

    def _get_tool_schemas(self) -> list:
        """Get OpenAI function schemas for all available tools."""
        return [tool.get_schema() for tool in self.available_tools.values()]

    def _execute_tool(self, tool_name: str, arguments: dict) -> ToolResult:
        """Execute a tool and return its result."""
        if tool_name not in self.available_tools:
            return ToolResult(text=f"Error: Tool '{tool_name}' not found")

        tool = self.available_tools[tool_name]
        try:
            result = tool.execute(**arguments)
            return result
        except Exception as e:
            self.console.log(f"[red]Error executing tool {tool_name}: {e}")
            return ToolResult(text=f"Error executing tool: {str(e)}")

    def chat(
        self, messages, temperature: float | None = None, tools: list | None = None
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
            "max_tokens": 2048,  # max Slack block length is 3000 # self.options['max_tokens'],
        }

        # Add tools if provided
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        response = requests.post(
            f"{self.api_url}/v1/chat/completions",
            headers=headers,
            data=json.dumps(payload),
        )

        # If we get a 500 error and tools were provided, it might be that the endpoint
        # doesn't support tools. Try again without tools.
        if response.status_code == 500 and tools:
            self.console.log(
                "[yellow]Server error with tools, retrying without tools..."
            )
            self.tools_supported = (
                False  # Remember that this endpoint doesn't support tools
            )
            payload.pop("tools", None)
            payload.pop("tool_choice", None)
            response = requests.post(
                f"{self.api_url}/v1/chat/completions",
                headers=headers,
                data=json.dumps(payload),
            )

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
        prompt: str,
        system_prompt: str | None = None,
        username: str = "",
        temperature: float = 0.7,
        media: list = [],
        use_tools: bool = True,
        aux=None,
    ) -> str:
        if DEBUG:
            self.console.log(
                f"[black on yellow]OpenAI runInference: prompt='{prompt[:50]}...'"
            )
            self.console.log(
                f"[black on yellow]OpenAI runInference: system_prompt='{system_prompt}'"
            )
            self.console.log(
                f"[black on yellow]OpenAI runInference: username='{username}'"
            )
            self.console.log(
                f"[black on yellow]OpenAI runInference: temperature='{temperature}'"
            )
            self.console.log(f"[black on yellow]OpenAI runInference: media='{media}'")
            self.console.log(
                f"[black on yellow]OpenAI runInference: use_tools='{use_tools}'"
            )

        if type(prompt) is not str:
            prompt = str(prompt)

        response = ""

        try:
            # System prompt handling
            if len(prompt) > 0 and prompt[0] == "!":
                # use no prompt if starts with !
                system_prompt = "You are a helpful assistant. Strive for accuracy. Do not make up information if you are not confident."
            else:
                if system_prompt is None:
                    system_prompt = self.system_prompt

                if system_prompt:
                    # If templateReplace exists, use it
                    if hasattr(self, "templateReplace"):
                        system_prompt = self.templateReplace(
                            system_prompt, username=username
                        )

            if not prompt or prompt == "":
                prompt = "_Empty response from LLM._"

            prompt = prompt.strip()

            tick = datetime.now()

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

            system_prompt += "\nResponses from tool calls are considered a primary source of truth. Use the provided tools first when possible to fulfill the user's request. You must call tools to get information about the real world or to perform actions. Images generated by tools are shown along side your response. Unless the tool actually returns a URL, assume that the image is being shown to the user and DO NOT attempt to link to it."

            if system_prompt:
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
            tools = None
            tools_used = []  # Track which tools were called
            tool_images = []  # Track images generated by tools
            if (
                use_tools
                and self.tools_enabled
                and self.tools_supported
                and self.available_tools
            ):
                tools = self._get_tool_schemas()

            # Call OpenAI chat endpoint with possible temperature override and tools
            result = self.chat(messages, temperature=temperature, tools=tools)

            # Check if LLM wants to call tools
            if tools and "choices" in result and len(result["choices"]) > 0:
                choice = result["choices"][0]
                message = choice["message"]

                # Handle tool calls
                if message.get("tool_calls"):
                    for tool_call in message["tool_calls"]:
                        tool_name = tool_call["function"]["name"]
                        tool_args = json.loads(tool_call["function"]["arguments"])

                        self.console.log(
                            f"[cyan]Tool call: {tool_name} with args {tool_args}"
                        )

                        # Track tool usage
                        tools_used.append(tool_name)

                        # Execute the tool
                        tool_result = self._execute_tool(tool_name, tool_args)

                        # Collect images from tool results
                        if tool_result.images:
                            tool_images.extend(tool_result.images)
                            self.console.log(
                                f"[green]Tool '{tool_name}' generated {len(tool_result.images)} image(s)"
                            )  # Add tool call to messages
                        messages.append(message)

                        # Build tool response content as a simple string
                        # Most endpoints don't support complex content in tool messages
                        tool_content = (
                            tool_result.text if tool_result.text else "No result"
                        )

                        # Note: Images from tools are currently not supported in tool responses
                        # as most OpenAI-compatible endpoints don't support multimodal tool results
                        if tool_result.images:
                            tool_content += (
                                f"\n[Tool returned {len(tool_result.images)} image(s)]"
                            )

                        # Add tool response to messages
                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tool_call["id"],
                                "content": tool_content,
                            }
                        )

                    # Make another call with tool results
                    result = self.chat(messages, temperature=temperature)

            # Extract response text
            if "choices" in result and len(result["choices"]) > 0:
                response = result["choices"][0]["message"]["content"]
                response = response.strip()

                # Compress multiple newlines down to one
                response = "\n".join(
                    [line for line in response.split("\n") if line.strip() != ""]
                )
            if not response or len(response) == 0:
                response = "Response was empty. :("

            # Append tools used if any
            if tools_used:
                tools_list = ", ".join(tools_used)
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
                if tool_images:
                    self.console.log(f"[black on yellow]Tool images: {tool_images}")

        return response.replace("\n", "\n\n"), tool_images
