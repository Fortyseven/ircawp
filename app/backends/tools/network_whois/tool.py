"""
Whois
"""

from ..ToolBase import tool


# Simple decorator usage - description from docstring
@tool
def network_whois(domain: str) -> str:
    """
    Perform a WHOIS lookup for a given domain.

    Args:
        domain: The domain name to look up
    """
    try:
        # let's do this from an exec
        import os

        result = os.popen(f"whois {domain}").read()
        return result
    except Exception as e:
        return f"Error performing WHOIS lookup. -- {e}"
