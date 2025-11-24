"""
Basic News Summary
"""

from app.backends.Ircawp_Backend import Ircawp_Backend
from app.lib.network import fetchHtml
from .__PluginBase import PluginBase
from bs4 import BeautifulSoup, Comment
import datetime


START_TIME = datetime.datetime.now()
SITE_URL = "https://drudgereport.com/"


def news(prompt: str, media: list, backend: Ircawp_Backend) -> tuple[str, str, bool]:
    content = fetchHtml(SITE_URL)

    # page has HTML comments bracketing sections of the site:
    # <! TOP LEFT STARTS HERE >
    # <! TOP LEFT HEADLINES END HERE>
    # <! MAIN HEADLINE >
    # <! MAIN HEADLINE END HERE>
    # then there's one <table> tag with all the other headlines inside
    headlines = []

    soup = BeautifulSoup(content, "html.parser")

    # Find all comments
    comments = soup.find_all(string=lambda text: isinstance(text, Comment))

    # Process TOP LEFT section
    for comment in comments:
        if "TOP LEFT STARTS HERE" in comment:
            current = comment.next_sibling
            while current:
                if (
                    isinstance(current, Comment)
                    and "TOP LEFT HEADLINES END HERE" in current
                ):
                    break
                if hasattr(current, "find_all"):
                    # Extract all links from this section
                    for link in current.find_all("a"):
                        text = link.get_text(strip=True)
                        href = link.get("href", "")
                        if text:
                            headlines.append((text, href))
                current = current.next_sibling
            break

    # Process MAIN HEADLINE section
    for comment in comments:
        if "MAIN HEADLINE" in comment and "END" not in comment:
            current = comment.next_sibling
            while current:
                if isinstance(current, Comment) and "MAIN HEADLINE END HERE" in current:
                    break
                if hasattr(current, "find_all"):
                    # Extract all links from this section
                    for link in current.find_all("a"):
                        text = link.get_text(strip=True)
                        href = link.get("href", "")
                        if text:
                            headlines.append((text, href))
                current = current.next_sibling
            break

    # Process main table (additional headlines)
    tables = soup.find_all("table")
    if tables and len(tables) >= 1:
        for row in tables[0].find_all("tr"):
            cols = row.find_all("td")
            if cols:
                for col in cols:
                    link = col.find("a")
                    if link:
                        text = link.get_text(strip=True)
                        href = link.get("href", "")
                        if text and text not in [
                            h[0] for h in headlines
                        ]:  # Avoid duplicates
                            headlines.append((text, href))

    if not headlines:
        return "No headlines found.", "", True

    # Format the headlines for display
    formatted_headlines = "\n".join(f"• {title} ({url})" for title, url in headlines)

    return "Drudge Report Headlines:\n" + formatted_headlines, "", False


plugin = PluginBase(
    name="Drudge Report Front Page",
    description="Dumps the current front page of the Drudge Report.",
    triggers=["news"],
    system_prompt="",
    emoji_prefix="",
    msg_empty_query="No prompt provided",
    msg_exception_prefix="GNUS PROBLEMS",
    main=news,
    use_imagegen=False,
    prompt_required=False,
)
