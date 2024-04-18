from datetime import datetime


def template_str(text: str, **kwargs) -> str:
    """
    A simple template string function.

    Currently only supports the `{today}` keyword,
    but you can add more if you want.
    """
    return text.format(
        today=datetime.now().strftime("%A, %B %d, %Y"),
        **kwargs,
    ).strip()


if __name__ == "__main__":
    print(template_str("Today is {today}. {ass}", ass="ASS!"))
