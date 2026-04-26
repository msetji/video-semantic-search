import logging
from collections import deque
from threading import Lock


class _InMemoryHandler(logging.Handler):
    def __init__(self, maxlen: int = 500) -> None:
        super().__init__()
        self._records: deque[dict] = deque(maxlen=maxlen)
        self._lock = Lock()

    def emit(self, record: logging.LogRecord) -> None:
        try:
            with self._lock:
                self._records.append({
                    "ts": record.created,
                    "level": record.levelname,
                    "logger": record.name,
                    "msg": self.format(record),
                })
        except Exception:
            self.handleError(record)

    def snapshot(self) -> list[dict]:
        with self._lock:
            return list(self._records)


_handler = _InMemoryHandler()


def setup_logging() -> None:
    fmt = logging.Formatter("%(levelname)s [%(name)s] %(message)s")
    _handler.setFormatter(fmt)
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    if _handler not in root.handlers:
        root.addHandler(_handler)


def get_log_records() -> list[dict]:
    return _handler.snapshot()
