"""Simple in-memory caching utilities.

Entries are stored with insertion timestamp and per-item TTL.
A cleanup pass runs on every read to purge expired items.
Not thread-safe; suitable for single-process usage.
"""

from time import time
from typing import Any, Dict, Tuple

# key -> (stored_at, ttl_seconds, value)
_store: Dict[str, Tuple[float, int, Any]] = {}
DEFAULT_TTL_SECONDS = 600  # 10 minutes


def set_cache(key: str, value: Any, ttl: int = DEFAULT_TTL_SECONDS) -> None:
    _store[key] = (time(), ttl, value)


def get_cache(key: str) -> Any:
    now = time()
    # Cleanup expired entries
    expired = [k for k, (t, ttl, _) in _store.items() if now - t > ttl]
    for k in expired:
        del _store[k]

    entry = _store.get(key)
    if entry is None:
        return None
    stored_at, ttl, value = entry
    if now - stored_at <= ttl:
        return value
    # Expired; remove and return None
    del _store[key]
    return None


def cache_size() -> int:
    return len(_store)


def clear_cache() -> None:
    _store.clear()
