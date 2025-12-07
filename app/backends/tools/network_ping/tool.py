"""
Ping
"""

from ..ToolBase import tool


# Simple decorator usage - description from docstring
@tool(
    name="network_ping",
    description="Ping a domain or IP address to check if it's reachable and measure network latency. Returns response times and packet loss information.",
    expertise_areas=[
        "networking",
        "connectivity",
        "diagnostics",
        "latency",
        "availability",
    ],
)
def network_ping(domain_or_ip: str) -> str:
    """
    Perform a ping for a given domain or IP address to test connectivity.

    Args:
        domain_or_ip: The domain name or IP address to ping (e.g., 'google.com', '8.8.8.8')
    """
    try:
        # let's do this from an exec
        import os

        result = os.popen(f"ping -c 2 {domain_or_ip}").read()
        return result
    except Exception as e:
        return f"Error performing WHOIS lookup. -- {e}"
