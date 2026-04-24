from __future__ import annotations

import threading
import time
from typing import Any

_lock = threading.Lock()
_status: str = "idle"
_detail: str | None = None
_last_result: dict[str, Any] | None = None
_error: str | None = None
_embedding_count: int = 0
_started_at: float | None = None
_finished_at: float | None = None


def reset_for_tests() -> None:
    global _status, _detail, _last_result, _error, _embedding_count, _started_at, _finished_at
    with _lock:
        _status = "idle"
        _detail = None
        _last_result = None
        _error = None
        _embedding_count = 0
        _started_at = None
        _finished_at = None


def is_running() -> bool:
    with _lock:
        return _status == "running"


def start() -> None:
    global _status, _detail, _error, _last_result, _embedding_count, _started_at, _finished_at
    with _lock:
        _status = "running"
        _detail = "indexing"
        _error = None
        _last_result = None
        _embedding_count = 0
        _started_at = time.time()
        _finished_at = None


def set_embedding_count(n: int) -> None:
    global _embedding_count
    with _lock:
        _embedding_count = n


def complete(result: dict[str, Any]) -> None:
    global _status, _detail, _last_result, _finished_at
    with _lock:
        _status = "completed"
        _detail = "done"
        _last_result = result
        _finished_at = time.time()


def fail(message: str) -> None:
    global _status, _detail, _error, _finished_at
    with _lock:
        _status = "failed"
        _detail = "error"
        _error = message
        _finished_at = time.time()


def snapshot() -> dict[str, Any]:
    with _lock:
        return {
            "status": _status,
            "detail": _detail,
            "error": _error,
            "embeddings_written": _embedding_count,
            "last_result": _last_result,
            "started_at": _started_at,
            "finished_at": _finished_at,
        }
