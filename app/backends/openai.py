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
        self.options["temperature"] = self.oai_config.get("temperature", 0.7)
        self.options["max_tokens"] = self.oai_config.get("max_tokens", 1024)

        self.console.log(f"- [yellow]OpenAI API URL: {self.api_url}[/yellow]")
        self.console.log(f"- [yellow]OpenAI Model: {self.model}[/yellow]")
        self.console.log(
            f"- [yellow]OpenAI Temperature: {self.options['temperature']}[/yellow]"
        )
        self.console.log(
            f"- [yellow]OpenAI Max Tokens: {self.options['max_tokens']}[/yellow]"
        )

        self.system_prompt = self.config.get("llm", {}).get("system_prompt", None)

        if not self.system_prompt:
            self.console.log(
                "[yellow]Warning: No system prompt set in config ('config.llm.system_prompt')[/yellow]"
            )

        self.console.log("System prompt: ", self.system_prompt)

    def chat(self, messages, temperature: float | None = None):
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
            # "max_tokens": self.options['max_tokens'],
        }
        response = requests.post(
            f"{self.api_url}/v1/chat/completions",
            headers=headers,
            data=json.dumps(payload),
        )
        response.raise_for_status()
        return response.json()

    def _image_to_data_uri(self, img_path: str) -> str | None:
        """Read local image file and return a data URI suitable for OpenAI image_url content part.

        Returns None if file cannot be read or is not an image.
        """
        try:
            p = Path(img_path)
            if not p.is_file():
                self.console.log(f"[yellow]Media file not found: {img_path}[/yellow]")
                return None
            mime, _ = mimetypes.guess_type(p.name)
            if not mime or not mime.startswith("image/"):
                self.console.log(
                    f"[yellow]Skipping non-image media: {img_path} (mime={mime})[/yellow]"
                )
                return None
            data = p.read_bytes()
            b64 = base64.b64encode(data).decode("utf-8")
            return f"data:{mime};base64,{b64}"
        except Exception as e:
            self.console.log(f"[yellow]Failed reading image '{img_path}': {e}[/yellow]")
            return None

    def runInference(
        self,
        prompt: str,
        system_prompt: str | None = None,
        username: str = "",
        temperature: float = 0.7,
        media: list = [],
    ) -> str:
        if type(prompt) is not str:
            self.console.log(f"= OpenAI runInference: prompt='{prompt}...'")
            prompt = str(prompt)

        response = ""
        try:
            # System prompt handling
            if prompt[0] == "!":
                # use no prompt if starts with !
                system_prompt = ""
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

            if system_prompt:
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ]
            else:
                messages = [
                    {"role": "user", "content": user_content},
                ]

            # Call OpenAI chat endpoint with possible temperature override
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

            tok = datetime.now()

            self.last_query_time = tok - tick

        except Exception as e:
            response = f"**IT HERTZ, IT HERTZ (openai):** '{e}'"
            self.console.log(f"[red]Exception in OpenAI backend: {e}[/red] {str(e)}")

        return response.replace("\n", "\n\n")
