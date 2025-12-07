"""
Whois
"""

from ..ToolBase import tool


# Simple decorator usage - description from docstring
@tool(
    name="network_whois",
    description="Look up domain registration information using WHOIS. Returns registrant details, registration date, nameservers, and other domain metadata.",
    expertise_areas=[
        "domain-information",
        "dns",
        "registration",
        "network-data",
        "web-infrastructure",
    ],
)
def network_whois(domain: str) -> str:
    """
    Perform a WHOIS lookup for a given domain to retrieve registration information.

    Args:
        domain: The domain name to look up (e.g., 'example.com', 'google.com')
    """
    try:
        # let's do this from an exec
        import os

        result = os.popen(f"whois {domain}").read()
        return result
    except Exception as e:
        return f"Error performing WHOIS lookup. -- {e}"
