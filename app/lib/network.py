import requests

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


def fetchHtml(
    url,
    timeout=12,
    allow_redirects=True,
    headers=None,
    text_only=False,
    use_js=False,
):
    if use_js:
        content = fetchHtmlWithJs(url, timeout=timeout, headers=headers)
        if isinstance(content, tuple):
            return content

        if text_only:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(content, "html.parser")
            return soup.get_text(separator="\n", strip=True)
        else:
            return content

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
            return soup.get_text(separator="\n", strip=True)
        else:
            return resp.text

    except Exception as e:
        return f"Error fetching URL: {e}", "", True

    except requests.exceptions.Timeout:
        return (
            f"Timed out while trying to fetch ({url}). Sites can be fussy; try again in a minute.",
            "",
            True,
        )
