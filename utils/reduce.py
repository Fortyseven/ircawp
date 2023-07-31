from bs4 import BeautifulSoup

# TODO:
# - de-dupe sentences
# - remove common non-relevant text (e.g. "click here to learn more", "Search", "Sign in", etc.)


def reduce_html(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    title = soup.find("title").text.strip()

    for x in ["noscript", "nav", "script", "svg", "title", "img", "aside"]:
        for y in soup.find_all(x):
            y.decompose()

    # classes to preemptively strike
    for x in [
        "sidebar",
        "ad-container",
        "ad",
        "article-meta",
        "sidebar-left",
        "sidebar-right",
        "newswire__wrapper",
    ]:
        for y in soup.find_all(class_=x):
            y.decompose()

    # let's see if we have an article first; gamble on it being used right
    article_el = soup.find("article")

    if article_el:
        clean_text = article_el.get_text().strip()
    else:
        clean_text = soup.get_text().strip()

    ## boil it down

    # removes duplicate whitespace
    clean_text = " ".join(clean_text.split())


    return clean_text, title
