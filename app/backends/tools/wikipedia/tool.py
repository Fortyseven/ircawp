"""
Wikipedia tool - provides information from Wikipedia.
"""

from urllib.parse import quote_plus
from ..ToolBase import tool
from app.lib.network import fetchHtml
import wikitextparser as wtp
from rich.console import Console
import re

DEBUG = True
console = Console()


def _extract_redirect_target(raw_content: str) -> str:
    """Extract the redirect target from Wikipedia redirect syntax.

    Example: '#REDIRECT [[Archer (2009 TV series)]]' -> 'Archer (2009 TV series)'

    Args:
        raw_content: Raw wikitext content starting with #REDIRECT

    Returns:
        The redirect target topic name, or empty string if not found
    """
    match = re.search(r"#REDIRECT\s*\[\[([^\]]+)\]\]", raw_content)
    if match:
        return match.group(1).strip()
    return ""


def _extract_infobox_data(parsed) -> str:
    """Extract and condense information from Wikipedia infobox templates."""
    infobox_lines = []

    for template in parsed.templates:
        template_name = template.name.strip().lower()

        # Check if this is an infobox template
        if template_name.startswith("infobox"):
            infobox_lines.append("**Infobox Data:**")

            # Extract arguments (key-value pairs)
            for arg in template.arguments:
                key = arg.name.strip()
                value_raw = arg.value.strip()

                # Skip empty values and image-related fields only
                if not value_raw or key.lower() in [
                    "image",
                    "caption",
                    "alt",
                    "image_size",
                    "signature",
                    "logo",
                    "image_caption",
                ]:
                    continue

                try:
                    # Parse the value to handle nested templates
                    parsed_value = wtp.parse(value_raw)

                    # Try to extract from nested templates like {{Plainlist|...}}
                    nested_items = []
                    for nested_template in parsed_value.templates:
                        if nested_template.name.strip().lower() in [
                            "plainlist",
                            "flatlist",
                            "unbulleted list",
                        ]:
                            # Get the content inside the plainlist
                            for nested_arg in nested_template.arguments:
                                if nested_arg.name.strip() in [
                                    "",
                                    "1",
                                ]:  # Unnamed or first argument
                                    # Parse the argument value
                                    content_text = nested_arg.value.strip()
                                    # Split by asterisks or newlines to get individual items
                                    lines = content_text.replace("*", "\n").split("\n")
                                    for line in lines:
                                        line = line.strip()
                                        if not line:
                                            continue
                                        # Parse each line to handle wikilinks but keep surrounding text
                                        parsed_line = wtp.parse(line)
                                        # Use plain_text to get the rendered text (expands wikilinks)
                                        clean_line = parsed_line.plain_text().strip()
                                        if clean_line:
                                            nested_items.append(clean_line)

                    # If we found nested items, use them
                    if nested_items:
                        clean_value = ", ".join(nested_items)
                    else:
                        # Fall back to plain text extraction
                        clean_value = parsed_value.plain_text().strip()
                        if not clean_value:
                            # Last resort: remove markup
                            clean_value = wtp.remove_markup(value_raw).strip()

                    if clean_value:
                        # Condense whitespace
                        clean_value = " ".join(clean_value.split())
                        # Truncate extremely long values but keep technical details
                        if len(clean_value) > 500:
                            clean_value = clean_value[:497] + "..."
                        infobox_lines.append(f"  • {key}: {clean_value}")
                except Exception as e:
                    if DEBUG:
                        console.log(f"[yellow]Error parsing infobox field '{key}': {e}")
                    continue

            # Only include first infobox
            break

    return "\n".join(infobox_lines) if len(infobox_lines) > 1 else ""


def _condense_wikitext(raw_wikitext: str, max_sections: int = 3) -> str:
    """
    Parse and condense Wikipedia wikitext into clean, readable text.

    Args:
        raw_wikitext: Raw wikitext markup from Wikipedia
        max_sections: Maximum number of main sections to include (default: 3)

    Returns:
        Condensed plain text with lead paragraph and key sections
    """
    try:
        parsed = wtp.parse(raw_wikitext)

        # Get all sections (section 0 is the lead/intro)
        sections = parsed.sections

        if not sections:
            return "No content found."

        result_parts = []

        # Extract infobox data first
        infobox_data = _extract_infobox_data(parsed)
        if infobox_data:
            result_parts.append(infobox_data)

        # Always include the lead section (before first heading)
        lead = sections[0].plain_text().strip()
        if lead:
            result_parts.append(lead)

        # Include first few main sections, excluding common metadata sections
        skip_sections = {
            "see also",
            "references",
            "external links",
            "notes",
            "further reading",
            "bibliography",
            "sources",
        }

        sections_added = 0
        for section in sections[1:]:
            if sections_added >= max_sections:
                break

            title = section.title.strip().lower() if section.title else ""

            # Skip metadata sections and empty sections
            if title in skip_sections or not section.plain_text().strip():
                continue

            # Add section with heading
            section_text = section.plain_text().strip()
            if section_text and section.title:
                result_parts.append(f"\n## {section.title.strip()}\n{section_text}")
                sections_added += 1

        return "\n\n".join(result_parts)

    except Exception as e:
        # Fallback: try to extract plain text from the whole thing
        try:
            return wtp.remove_markup(raw_wikitext)[:5000]  # Limit fallback size
        except Exception:
            return f"Error parsing wikitext: {str(e)}"


def _fetch_wikipedia_article(base_topic: str) -> str:
    """Internal function to fetch and process Wikipedia articles.

    Handles redirect detection and automatic resolution.

    Args:
        base_topic: The Wikipedia article title to fetch

    Returns:
        Condensed article content or error message
    """
    url_query = f"https://en.wikipedia.org/w/index.php?action=raw&title={quote_plus(base_topic)}"
    raw_content = fetchHtml(url_query, allow_redirects=True, timeout=12)

    if DEBUG:
        console.log("[cyan]WIKIPEDIA TOOL FETCHED URL:", url_query)
        console.log(f"[cyan]WIKIPEDIA RAW CONTENT LENGTH: {len(raw_content)} chars")

    # Check for redirect or missing page
    if raw_content.startswith("#REDIRECT"):
        redirect_target = _extract_redirect_target(raw_content)
        if redirect_target:
            if DEBUG:
                console.log(
                    f"[cyan]REDIRECT DETECTED: '{base_topic}' -> '{redirect_target}'"
                )
            # Recursively follow the redirect
            return _fetch_wikipedia_article(redirect_target)
        else:
            return f"Error: '{base_topic}' is a redirect page but the target could not be determined."

    if "Wikipedia does not have an article" in raw_content[:200]:
        return f"Wikipedia does not have an article titled '{base_topic}'."

    # Parse and condense the wikitext
    condensed = _condense_wikitext(raw_content, max_sections=3)

    # Add source link
    wiki_link = f"https://en.wikipedia.org/wiki/{base_topic.replace(' ', '_')}"
    result = f"{condensed}\n\nSource: {wiki_link}"

    if DEBUG:
        console.log(f"[green]WIKIPEDIA CONDENSED LENGTH: {len(result)} chars")

    return result


@tool(
    expertise_areas=[
        "knowledge",
        "research",
        "facts",
        "definitions",
        "history",
        "biography",
        "general-information",
    ]
)
def wikipedia(base_topic: str) -> str:
    """Search Wikipedia to get more information about a topic. Use only the most general and widely recognized name or topic (e.g., 'CNN', 'Albert Einstein') to retrieve relevant Wikipedia content. Avoid adding qualifiers like 'launch date', 'birth date', or 'history' unless absolutely necessary."""
    try:
        result = _fetch_wikipedia_article(base_topic)
        return result, "", False
    except Exception as e:
        return f"WIKIPEDIA PROBLEMS: {str(e)}", "", True, {}
