import requests

DEFAULT_UA = "Mozilla/5.0 (X11; Linux x86_64; rv:145.0) Gecko/20100101 Firefox/145.0"


def fetchHtml(url, timeout=10, headers=None, text_only=False):
    try:
        if headers is None:
            headers = {
                "User-Agent": DEFAULT_UA,
            }
        resp = requests.get(url, timeout=timeout, headers=headers)
        resp.raise_for_status()

        if text_only:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(resp.text, "html.parser")
            return soup.get_text(separator="\n", strip=True)
        else:
            return resp.text

    except Exception as e:
        return f"Error fetching URL: {e}", "", True
