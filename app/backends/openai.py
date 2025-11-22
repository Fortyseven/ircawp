"""
Backend for OpenAI-compatible endpoints (e.g., api.openai.com, local LLMs with OpenAI API).
"""
import requests
import json
from .Ircawp_Backend import Ircawp_Backend

class Openai(Ircawp_Backend):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.config = kwargs.get("config", {})

        if not "openai" in self.config:
            raise ValueError("Missing OpenAI backend configuration ('config.openai')")

        self.oai_config = self.config.get("openai", {})


        if (not "api_url" in self.oai_config):
            raise ValueError("Missing OpenAI endpoint ('config.openai.api_url')")

        self.api_url = self.oai_config["api_url"].rstrip("/")
        self.api_key = self.oai_config.get("api_key", '')
        self.model = self.oai_config.get("model", '')

        self.options = {}
        self.options['temperature'] = self.oai_config.get("temperature", 0.7)
        self.options['max_tokens'] = self.oai_config.get("max_tokens", 1024)

        self.console.log(f"- [yellow]OpenAI API URL: {self.api_url}[/yellow]")
        self.console.log(f"- [yellow]OpenAI Model: {self.model}[/yellow]")
        self.console.log(f"- [yellow]OpenAI Temperature: {self.options['temperature']}[/yellow]")
        self.console.log(f"- [yellow]OpenAI Max Tokens: {self.options['max_tokens']}[/yellow]")

        self.system_prompt = self.config.get("llm", {}).get("system_prompt", None)

        if not self.system_prompt:
            self.console.log("[yellow]Warning: No system prompt set in config ('config.llm.system_prompt')[/yellow]")

        self.console.log("System prompt: ", self.system_prompt)

    def chat(self, messages):
        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.options['temperature'],
            # "max_tokens": self.options['max_tokens'],
        }
        response = requests.post(
            f"{self.api_url}/v1/chat/completions",
            headers=headers,
            data=json.dumps(payload)
        )
        response.raise_for_status()
        return response.json()

    def runInference(
        self,
        prompt: str,
        system_prompt: str | None = None,
        username: str = "",
    ) -> str:
        response = ""
        try:
            # System prompt handling
            if prompt[0] == '!':
                # use no prompt if starts with !
                system_prompt = ''
            else:
                if system_prompt is None:
                    system_prompt = self.system_prompt

                if system_prompt:
                    # If templateReplace exists, use it
                    if hasattr(self, "templateReplace"):
                        system_prompt = self.templateReplace(system_prompt, username=username)

            prompt = prompt.strip()

            # Compose messages for chat endpoint
            messages = []
            if system_prompt:
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ]
            else:
                messages = [
                    {"role": "user", "content": prompt},
                ]

            # Call OpenAI chat endpoint
            result = self.chat(messages)
            # Extract response text
            response = result["choices"][0]["message"]["content"].strip()

            # Compress multiple newlines down to one
            response = "\n".join([line for line in response.split("\n") if line.strip() != ""])
            if len(response) == 0:
                response = "Response was empty. :("
        except Exception as e:
            response = f"**IT HERTZ, IT HERTZ (openai):** '{str(e)}'"
        return response.replace("\n", "\n\n")
