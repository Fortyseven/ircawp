"""Media backend client module.

The MediaBackend class is now an HTTP client to the media-server.
Backend implementations live in media-server/app/backends/.
"""

from .MediaBackend import MediaBackend

__all__ = ["MediaBackend"]
