"""
Ping
"""

from ..ToolBase import tool


# Simple decorator usage - description from docstring
@tool
def network_ping(domain_or_ip: str) -> str:
    """
    Perform a ping for a given domain or ip.

    Args:
        domain: The domain name to look up
    """
    try:
        # let's do this from an exec
        import os

        result = os.popen(f"ping -c 2 {domain_or_ip}").read()
        return result
    except Exception as e:
        return f"Error performing WHOIS lookup. -- {e}"
