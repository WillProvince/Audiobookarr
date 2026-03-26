import collections
import logging
import threading

_MAX_RECORDS = 2000  # keep the last 2000 records in memory


class RingBufferHandler(logging.Handler):
    """Thread-safe in-memory ring buffer that keeps the last N log records."""

    def __init__(self, capacity: int = _MAX_RECORDS):
        super().__init__()
        self._capacity = capacity
        self._lock = threading.Lock()
        self._buffer: collections.deque = collections.deque(maxlen=capacity)

    def emit(self, record: logging.LogRecord) -> None:
        with self._lock:
            self._buffer.append(record)

    def get_records(self, min_level: int = logging.DEBUG) -> list:
        with self._lock:
            return [r for r in self._buffer if r.levelno >= min_level]

    def clear(self) -> None:
        with self._lock:
            self._buffer.clear()


# Module-level singleton — attached to the root logger in create_app()
ring_handler = RingBufferHandler()
