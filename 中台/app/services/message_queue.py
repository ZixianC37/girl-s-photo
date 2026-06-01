"""Synchronous rate-limited message queue for P0 implementation."""

import time
from collections import deque
from typing import Callable, Any


class MessageQueue:
    """A simple synchronous message queue with rate limiting.

    This queue processes messages sequentially with a configurable rate limit.
    Suitable for P0 implementation where simplicity is preferred over complexity.

    Args:
        rate_per_minute: Maximum number of messages to process per minute.
    """

    def __init__(self, rate_per_minute: int = 20):
        self._queue: deque[tuple[Callable, tuple, dict]] = deque()
        self._interval = 60.0 / rate_per_minute  # seconds between messages

    def enqueue(self, callback: Callable, *args: Any, **kwargs: Any) -> None:
        """Add a message to the queue.

        Args:
            callback: The function to call when processing this message.
            *args: Positional arguments to pass to the callback.
            **kwargs: Keyword arguments to pass to the callback.
        """
        self._queue.append((callback, args, kwargs))

    def drain(self) -> int:
        """Process all queued messages sequentially with rate limiting.

        This method blocks until all messages are processed.
        Each message is separated by the rate limit interval.

        Returns:
            The number of messages processed.
        """
        sent = 0
        while self._queue:
            callback, args, kwargs = self._queue.popleft()
            callback(*args, **kwargs)
            sent += 1
            if self._queue:  # don't sleep after last message
                time.sleep(self._interval)
        return sent

    def pending_count(self) -> int:
        """Get the number of messages currently in the queue.

        Returns:
            The number of pending messages.
        """
        return len(self._queue)

    def clear(self) -> None:
        """Remove all messages from the queue without processing them."""
        self._queue.clear()
