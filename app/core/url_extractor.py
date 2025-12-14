"""URL extraction and content fetching."""

import re
from typing import Optional
from rich.console import Console


class URLExtractor:
    """Handles URL extraction from text and content fetching."""

    def __init__(self, console: Console):
        """
        Initialize the URL extractor.

        Args:
            console: Rich console for logging
        """
        self.console = console
        # Exclude < and > which are common delimiters (e.g. in Slack)
        self.url_pattern = re.compile(r"(https?://[^\s<>]+)")

    def extract_url(self, text: str) -> Optional[str]:
        """
        Extract the first URL from the given text.

        Args:
            text: The text to extract URLs from

        Returns:
            The first extracted URL, or None if no URLs found
        """
        urls = self.url_pattern.findall(text)

        if not urls:
            return None

        url = urls[0]

        # Strip common trailing punctuation
        while url and url[-1] in ".,!?:;":
            url = url[:-1]

        # Handle trailing parenthesis (e.g. inside brackets)
        if url.endswith(")"):
            opens = url.count("(")
            closes = url.count(")")
            if closes > opens:
                url = url[:-1]

        return url

    def fetch_url_content(
        self, url: str, text_only: bool = True, use_js: bool = True
    ) -> Optional[str]:
        """
        Fetch and return content from a URL.

        Args:
            url: The URL to fetch
            text_only: Whether to extract only text content
            use_js: Whether to use JavaScript rendering

        Returns:
            The fetched content, or None on error
        """
        try:
            from app.lib.network import fetchHtml

            content = fetchHtml(url, text_only=text_only, use_js=use_js)
            return content
        except Exception as e:
            self.console.log(f"[red]Error fetching URL {url}: {e}")
            return None

    def augment_message_with_url(self, message: str) -> str:
        """
        Extract URL from message, fetch its content, and augment the message.

        Args:
            message: The original message text

        Returns:
            The augmented message with URL content, or original if no URL
        """
        url = self.extract_url(message)

        if not url:
            return message

        content = self.fetch_url_content(url, text_only=True, use_js=True)

        if not content:
            # If we can't fetch content, just return original message
            return message

        # Prepend URL content to the message
        augmented = f"####{url} content: ```\n{content}\n```\n####\n\n{message}"
        return augmented
