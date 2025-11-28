import requests
from . import cache
import hashlib


DEFAULT_UA = "Mozilla/5.0 (X11; Linux x86_64; rv:145.0) Gecko/20100101 Firefox/145.0"


def fetchHtmlWithJs(url, timeout=12, headers=None):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return (
            "Error: Playwright is not installed. Please install it with `pip install playwright` and run `playwright install`.",
            "",
            True,
        )

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)

            context_args = {"user_agent": DEFAULT_UA}
            if headers:
                context_args["extra_http_headers"] = headers

            context = browser.new_context(**context_args)
            page = context.new_page()
            page.goto(url, timeout=timeout * 1000)

            try:
                page.wait_for_load_state("networkidle", timeout=timeout * 1000)
            except Exception:
                pass

            content = page.content()
            browser.close()
            return content
    except Exception as e:
        return f"Error fetching URL with JS: {e}", "", True


def _make_cache_key(url, timeout, allow_redirects, headers, text_only, use_js):
    # Normalize headers for key stability
    headers_tuple = tuple(sorted((headers or {}).items()))
    raw = f"{url}|{timeout}|{allow_redirects}|{headers_tuple}|{text_only}|{use_js}"
    return hashlib.sha256(raw.encode()).hexdigest()


def fetchHtml(
    url,
    timeout=12,
    allow_redirects=True,
    headers=None,
    text_only=False,
    use_js=False,
    bypass_cache=False,
) -> str:
    """Fetch HTML (optionally rendered with JS) with optional caching.

    Successful responses are cached for ~10 minutes. Cache key factors:
    url, timeout, allow_redirects, headers, text_only, use_js.

    Args:
        url: Target URL.
        timeout: Seconds before timing out.
        allow_redirects: Follow redirects when using requests.
        headers: Optional dict of headers.
        text_only: If True, returns extracted visible text.
        use_js: If True, uses Playwright to render.
        bypass_cache: If True, forces a fresh fetch and updates cache.
    Returns:
        str on success or throws error string on failure.
    """
    cache_key = _make_cache_key(
        url, timeout, allow_redirects, headers, text_only, use_js
    )
    if not bypass_cache:
        cached = cache.get_cache(cache_key)
        if cached is not None:
            print(f"[fetchHtml] cache hit: {url}")
            return cached
        else:
            print(f"[fetchHtml] cache miss: {url}")
    else:
        print(f"[fetchHtml] cache bypass requested: {url}")

    if use_js:
        content = fetchHtmlWithJs(url, timeout=timeout, headers=headers)
        if isinstance(content, tuple):
            return content  # Error; do not cache

        if text_only:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(content, "html.parser")
            result = soup.get_text(separator="\n", strip=True)
        else:
            result = content

        # Cache successful result
        print(f"[fetchHtml] cache store: {url}")
        cache.set_cache(cache_key, result)
        return result

    try:
        if headers is None:
            headers = {
                "User-Agent": DEFAULT_UA,
            }
        resp = requests.get(
            url, timeout=timeout, headers=headers, allow_redirects=allow_redirects
        )
        resp.raise_for_status()

        if text_only:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(resp.text, "html.parser")
            result = soup.get_text(separator="\n", strip=True)
        else:
            result = resp.text

        cache.set_cache(cache_key, result)
        print(f"[fetchHtml] cache store: {url}")
        return result

    # except Exception as e:
    #     raise f"Error fetching URL: {e}"

    except requests.exceptions.Timeout:
        return f"Timed out while trying to fetch ({url}). Sites can be fussy; try again in a minute."
