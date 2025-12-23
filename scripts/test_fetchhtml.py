#!/usr/bin/env python3
"""
Simple tool to test fetchHtml functionality.
Usage: python scripts/test_fetchhtml.py <url> [options]

Options:
  --text-only    Extract only visible text
  --use-js       Render with JavaScript (requires Playwright)
  --bypass-cache Force fresh fetch, bypass cache
  --timeout N    Set timeout in seconds (default: 12)
  --snippet N    Show first N lines of output (default: show all)
  --check-bot    Check for bot detection patterns
"""

import sys
import argparse
from pathlib import Path

# Add parent directory to path so we can import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.lib.network import fetchHtml


BOT_DETECTION_PATTERNS = [
    "javascript disabled",
    "javascript required",
    "robot",
    "bot detected",
    "automated",
    "browser appears",
    "enable javascript",
    "access denied",
    "challenge",
    "press & hold",
]


def check_for_bot_detection(text):
    """Check if response contains bot detection indicators."""
    text_lower = text.lower()
    detected = []
    for pattern in BOT_DETECTION_PATTERNS:
        if pattern in text_lower:
            detected.append(pattern)
    return detected


def main():
    parser = argparse.ArgumentParser(
        description="Test fetchHtml functionality",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("url", help="URL to fetch")
    parser.add_argument(
        "--text-only",
        action="store_true",
        help="Extract only visible text",
    )
    parser.add_argument(
        "--use-js",
        action="store_true",
        help="Render with JavaScript (requires Playwright)",
    )
    parser.add_argument(
        "--bypass-cache",
        action="store_true",
        help="Force fresh fetch, bypass cache",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=12,
        help="Timeout in seconds (default: 12)",
    )
    parser.add_argument(
        "--snippet",
        type=int,
        default=None,
        help="Show first N lines of output",
    )
    parser.add_argument(
        "--check-bot",
        action="store_true",
        help="Check for bot detection patterns",
    )

    args = parser.parse_args()

    try:
        print(f"Fetching: {args.url}")
        print(f"  text_only: {args.text_only}")
        print(f"  use_js: {args.use_js}")
        print(f"  bypass_cache: {args.bypass_cache}")
        print(f"  timeout: {args.timeout}")
        print("-" * 80)

        result = fetchHtml(
            args.url,
            text_only=args.text_only,
            use_js=args.use_js,
            bypass_cache=args.bypass_cache,
            timeout=args.timeout,
        )

        if args.check_bot:
            detected = check_for_bot_detection(result)
            if detected:
                print("⚠️  Bot detection patterns found:", detected)
                print()

        if args.snippet:
            lines = result.split("\n")
            print("\n".join(lines[: args.snippet]))
            if len(lines) > args.snippet:
                print(f"\n... ({len(lines) - args.snippet} more lines)")
        else:
            print(result)

        print("-" * 80)
        print(f"✓ Successfully fetched {len(result)} characters")

    except Exception as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
