"""
Wikipedia tool - provides information from Wikipedia.
"""

import html
import json
import re
from urllib.parse import quote_plus

import wikitextparser as wtp
from rich.console import Console

from ..ToolBase import tool
from app.lib.network import fetchHtml

DEBUG = True
SEARCH_RESULTS_LIMIT = 5
CONTENT_VOTE_MAX_CANDIDATES = 5
CONTENT_VOTE_MAX_CHARS = 1200
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


def _clean_snippet(snippet: str) -> str:
    """Remove HTML tags and condense whitespace in snippets from the search API."""

    cleaned = html.unescape(snippet or "")
    cleaned = re.sub(r"<[^>]+>", "", cleaned)
    return " ".join(cleaned.split())


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


def _safe_truncate(text: str, limit: int) -> str:
    """Truncate text to a safe length for prompts."""

    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def _fetch_wikipedia_article(
    base_topic: str, max_sections: int = 3
) -> tuple[bool, str]:
    """Internal function to fetch and process Wikipedia articles with redirect handling."""
    url_query = f"https://en.wikipedia.org/w/index.php?action=raw&title={quote_plus(base_topic)}"
    raw_content = fetchHtml(url_query, allow_redirects=True, timeout=12)

    if DEBUG:
        console.log("[cyan]WIKIPEDIA TOOL FETCHED URL:", url_query)
        console.log(f"[cyan]WIKIPEDIA RAW CONTENT LENGTH: {len(raw_content)} chars")

    if isinstance(raw_content, str) and raw_content.startswith("[fetchHtml]"):
        return False, raw_content

    if not isinstance(raw_content, str):
        raw_content = str(raw_content)

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
            return (
                False,
                f"Error: '{base_topic}' is a redirect page but the target could not be determined.",
            )

    if "Wikipedia does not have an article" in raw_content[:200]:
        return False, f"Wikipedia does not have an article titled '{base_topic}'."

    # Parse and condense the wikitext
    condensed = _condense_wikitext(raw_content, max_sections=max_sections)

    # Add source link
    wiki_link = f"https://en.wikipedia.org/wiki/{base_topic.replace(' ', '_')}"
    result = f"{condensed}\n\nSource: {wiki_link}"

    if DEBUG:
        console.log(f"[green]WIKIPEDIA CONDENSED LENGTH: {len(result)} chars")

    return True, result


def _search_wikipedia(query: str, limit: int = SEARCH_RESULTS_LIMIT) -> list[dict]:
    """Search Wikipedia using the MediaWiki API and return candidate titles/snippets."""

    search_url = (
        "https://en.wikipedia.org/w/api.php?"
        f"action=query&list=search&format=json&utf8=1&srlimit={limit}&srsearch={quote_plus(query)}"
    )

    raw_json = fetchHtml(search_url, allow_redirects=True, timeout=8, bypass_cache=True)

    if DEBUG:
        console.log("[cyan]WIKIPEDIA SEARCH URL:", search_url)

    if isinstance(raw_json, str) and raw_json.startswith("[fetchHtml]"):
        return []

    try:
        data = json.loads(raw_json)
        search_results = data.get("query", {}).get("search", [])

        candidates = []
        for entry in search_results:
            title = (entry.get("title") or "").strip()
            snippet = _clean_snippet(entry.get("snippet") or "")

            if title:
                candidates.append(
                    {
                        "title": title,
                        "snippet": snippet,
                    }
                )

        return candidates[:limit]
    except Exception as e:
        if DEBUG:
            console.log(f"[yellow]Error parsing search response: {e}")
        return []


def _select_candidate_with_llm(query: str, candidates: list[dict], backend=None) -> int:
    """Use the LLM to pick the best matching search result.

    Returns the index of the chosen candidate (0-based) or -1 if none selected.
    """

    if not candidates or backend is None:
        return -1

    candidate_lines = []
    for idx, candidate in enumerate(candidates, start=1):
        candidate_lines.append(
            f"{idx}. Title: {candidate['title']}\n   Snippet: {candidate['snippet']}"
        )

    prompt = (
        "You are selecting the single best Wikipedia search result for a user query. "
        "Respond with only the number of the best match (1-{n}) or 0 if none cover the request.".format(
            n=len(candidates)
        )
        + "\n\nUser query: "
        + query
        + "\n\nCandidates:\n"
        + "\n".join(candidate_lines)
    )

    try:
        response, _ = backend.runInference(
            prompt=prompt,
            system_prompt="Select the best Wikipedia article candidate for the user's request.",
            use_tools=False,
            temperature=0.0,
        )
    except Exception as e:
        if DEBUG:
            console.log(f"[yellow]LLM selection failed: {e}")
        return -1

    match = re.search(r"\d+", response)
    if not match:
        return -1

    choice = int(match.group())
    if 1 <= choice <= len(candidates):
        return choice - 1

    return -1


def _select_candidate_with_content(
    query: str, candidates: list[dict], backend=None
) -> int:
    """Use condensed article content to pick the best match.

    Fetches and condenses up to CONTENT_VOTE_MAX_CANDIDATES pages with a very small
    footprint (lead + infobox), then asks the LLM to pick the best. Returns index or -1.
    """

    if not candidates or backend is None:
        return -1

    limited_candidates = candidates[:CONTENT_VOTE_MAX_CANDIDATES]
    condensed_blurbs: list[tuple[int, str]] = []

    for idx, candidate in enumerate(limited_candidates):
        success, condensed = _fetch_wikipedia_article(
            candidate["title"], max_sections=1
        )
        if not success:
            continue
        condensed_blurbs.append(
            (
                idx,
                _safe_truncate(condensed, CONTENT_VOTE_MAX_CHARS),
            )
        )

    if not condensed_blurbs:
        return -1

    lines = []
    for original_idx, blob in condensed_blurbs:
        title = candidates[original_idx]["title"]
        snippet = candidates[original_idx].get("snippet", "")
        lines.append(
            f"{original_idx + 1}. Title: {title}\n   Snippet: {snippet}\n   Content: {blob}"
        )

    prompt = (
        "Select the single best Wikipedia article for the user query using the provided condensed content. "
        "Respond with only the number of the best match (1-{n}) or 0 if none cover the request.".format(
            n=len(candidates)
        )
        + "\n\nUser query: "
        + query
        + "\n\nCandidates (with condensed content):\n"
        + "\n".join(lines)
    )

    try:
        response, _ = backend.runInference(
            prompt=prompt,
            system_prompt="Select the best Wikipedia article candidate using condensed page content.",
            use_tools=False,
            temperature=0.0,
        )
    except Exception as e:
        if DEBUG:
            console.log(f"[yellow]LLM content selection failed: {e}")
        return -1

    match = re.search(r"\d+", response)
    if not match:
        return -1

    choice = int(match.group())
    if 1 <= choice <= len(candidates):
        return choice - 1

    return -1


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
def wikipedia(base_topic: str, backend=None) -> str:
    """Search Wikipedia to get more information about a topic. Use only the most general and widely recognized name or topic (e.g., 'CNN', 'Albert Einstein') to retrieve relevant Wikipedia content. Avoid adding qualifiers like 'launch date', 'birth date', or 'history' unless absolutely necessary."""
    try:
        success, result = _fetch_wikipedia_article(base_topic)
        if success:
            return result, "", False

        # Attempt search fallback when the direct page is missing
        candidates = _search_wikipedia(base_topic, limit=SEARCH_RESULTS_LIMIT)
        if not candidates:
            return (
                f"Wikipedia does not have an article titled '{base_topic}', and no close matches were found via search.",
                "",
                True,
            )

        chosen_idx = _select_candidate_with_llm(base_topic, candidates, backend)

        # If multiple candidates or no initial pick, run a second pass using condensed content
        if backend and (chosen_idx == -1 or len(candidates) > 1):
            try:
                console.log(
                    f"[cyan]WIKIPEDIA content vote: {len(candidates)} candidates for '{base_topic}'"
                )
            except Exception:
                pass
            content_idx = _select_candidate_with_content(
                base_topic, candidates, backend
            )
            if content_idx != -1:
                chosen_idx = content_idx

        if chosen_idx == -1:
            titles = ", ".join(candidate["title"] for candidate in candidates)
            return (
                f"No direct article for '{base_topic}'. Closest search titles: {titles}",
                "",
                True,
            )

        selected_title = candidates[chosen_idx]["title"]

        success, result = _fetch_wikipedia_article(selected_title)
        if success:
            return f"Matched to '{selected_title}' via search.\n\n{result}", "", False

        # Try remaining candidates before giving up
        for idx, candidate in enumerate(candidates):
            if idx == chosen_idx:
                continue
            retry_success, retry_result = _fetch_wikipedia_article(candidate["title"])
            if retry_success:
                return (
                    f"Matched to '{candidate['title']}' via search fallback.\n\n{retry_result}",
                    "",
                    False,
                )

        return (
            f"Wikipedia does not have an article titled '{base_topic}', and the top search results did not resolve to usable pages.",
            "",
            True,
        )

    except Exception as e:
        return f"WIKIPEDIA PROBLEMS: {str(e)}", "", True, {}
