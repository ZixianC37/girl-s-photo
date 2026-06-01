"""Event deduplication with TTL-based cleanup"""
import time


class EventDedup:
    """
    In-memory event deduplication with TTL.

    Tracks processed event keys and automatically expires entries
    after the specified TTL (default: 300 seconds).
    """

    def __init__(self, ttl: int = 300):
        """
        Initialize the deduplication cache.

        Args:
            ttl: Time-to-live in seconds before entries expire
        """
        self._seen: dict[str, float] = {}  # key → timestamp
        self._ttl = ttl

    def is_duplicate(self, key: str) -> bool:
        """
        Check if an event key has already been processed.

        Args:
            key: Unique event identifier

        Returns:
            True if the key exists in cache (duplicate), False otherwise
        """
        self._cleanup()
        return key in self._seen

    def mark_processed(self, key: str) -> None:
        """
        Mark an event as processed by adding it to the cache.

        Args:
            key: Unique event identifier
        """
        self._seen[key] = time.time()

    def _cleanup(self) -> None:
        """
        Remove expired entries from the cache.

        This method is called automatically on each is_duplicate check
        to keep the cache size bounded.
        """
        now = time.time()
        expired = [k for k, t in self._seen.items() if now - t > self._ttl]
        for k in expired:
            del self._seen[k]
