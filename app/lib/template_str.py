from datetime import datetime


def template_str(text: str, **kwargs) -> str:
    """
    Simple and safe placeholder replacement for prompt strings.

    Supported built-ins:
    - {today}: weekday/month/day/year string
    - {current_datetime}: weekday + ISO-like date + 12-hour time (lowercase am/pm)

    Unknown placeholders are left untouched.
    """
    now = kwargs.pop("now", datetime.now())
    hour_12 = now.hour % 12 or 12
    current_datetime = (
        f"{now.strftime('%A')}, {now.strftime('%Y-%m-%d')} "
        f"at {hour_12}:{now.strftime('%M')}{now.strftime('%p').lower()}"
    )

    values = {
        "today": now.strftime("%A, %B %d, %Y"),
        "current_datetime": current_datetime,
        **kwargs,
    }

    rendered = text
    for key, value in values.items():
        rendered = rendered.replace(f"{{{key}}}", str(value))

    return rendered.strip()


if __name__ == "__main__":
    print(template_str("Now: {current_datetime}. Today is {today}. {ass}", ass="ASS!"))
