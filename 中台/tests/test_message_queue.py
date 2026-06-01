"""Tests for the message queue service."""

import time
from app.services.message_queue import MessageQueue


def test_queue_processes_all_messages():
    """Test that the queue processes all messages in order."""
    q = MessageQueue(rate_per_minute=600)  # high rate for fast test
    sent = []
    def sender(msg):
        sent.append(msg)

    for i in range(5):
        q.enqueue(sender, f"msg_{i}")

    q.drain()
    assert len(sent) == 5
    assert sent == ["msg_0", "msg_1", "msg_2", "msg_3", "msg_4"]


def test_queue_respects_rate_limit():
    """Test that the queue respects the rate limit."""
    q = MessageQueue(rate_per_minute=60)  # 1 per second
    sent = []
    def sender(msg):
        sent.append(msg)

    for i in range(3):
        q.enqueue(sender, f"msg_{i}")

    start = time.time()
    q.drain()
    elapsed = time.time() - start
    # 3 messages at 1/sec should take at least 2 seconds (gaps between sends)
    assert elapsed >= 1.5  # allow small margin


def test_queue_empty_drain():
    """Test that draining an empty queue does not error."""
    q = MessageQueue()
    result = q.drain()  # should not error
    assert result == 0


def test_queue_enqueue_returns_count():
    """Test that we can track the number of pending messages."""
    q = MessageQueue()
    q.enqueue(lambda x: x, "msg1")
    q.enqueue(lambda x: x, "msg2")
    assert q.pending_count() == 2


def test_queue_clear():
    """Test that clearing the queue removes all pending messages."""
    q = MessageQueue()
    q.enqueue(lambda x: x, "msg1")
    q.enqueue(lambda x: x, "msg2")
    assert q.pending_count() == 2
    q.clear()
    assert q.pending_count() == 0


def test_queue_drain_returns_count():
    """Test that drain returns the count of processed messages."""
    q = MessageQueue(rate_per_minute=600)
    for i in range(3):
        q.enqueue(lambda x: x, f"msg_{i}")
    result = q.drain()
    assert result == 3


def test_queue_with_kwargs():
    """Test that callbacks work with keyword arguments."""
    q = MessageQueue(rate_per_minute=600)
    sent = []
    def sender(msg, prefix=""):
        sent.append(f"{prefix}{msg}")

    q.enqueue(sender, "msg1", prefix="[")
    q.enqueue(sender, "msg2", prefix="]")

    q.drain()
    assert sent == ["[msg1", "]msg2"]


def test_queue_empty_after_drain():
    """Test that the queue is empty after draining."""
    q = MessageQueue(rate_per_minute=600)
    q.enqueue(lambda x: x, "msg1")
    q.enqueue(lambda x: x, "msg2")
    assert q.pending_count() == 2
    q.drain()
    assert q.pending_count() == 0
