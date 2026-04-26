from __future__ import annotations

import threading
import time
from typing import Any

_lock = threading.Lock()
_cancel_event = threading.Event()
_status: str = "idle"
_detail: str | None = None
_last_result: dict[str, Any] | None = None
_error: str | None = None
_embedding_count: int = 0
_started_at: float | None = None
_finished_at: float | None = None
_current_file: str | None = None
_total_files: int = 0
_files_done: int = 0


def reset_for_tests() -> None:
    global _status, _detail, _last_result, _error, _embedding_count, _started_at, _finished_at, _current_file, _total_files, _files_done
    with _lock:
        _status = "idle"
        _detail = None
        _last_result = None
        _error = None
        _embedding_count = 0
        _started_at = None
        _finished_at = None
        _current_file = None
        _total_files = 0
        _files_done = 0


def is_running() -> bool:
    with _lock:
        return _status == "running"


def start() -> None:
    global _status, _detail, _error, _last_result, _embedding_count, _started_at, _finished_at, _current_file, _total_files, _files_done
    _cancel_event.clear()
    with _lock:
        _status = "running"
        _detail = "indexing"
        _error = None
        _last_result = None
        _embedding_count = 0
        _started_at = time.time()
        _finished_at = None
        _current_file = None
        _total_files = 0
        _files_done = 0


def set_embedding_count(n: int) -> None:
    global _embedding_count
    with _lock:
        _embedding_count = n


def set_file_progress(current_file: str, files_done: int, total_files: int) -> None:
    global _current_file, _files_done, _total_files
    with _lock:
        _current_file = current_file
        _files_done = files_done
        _total_files = total_files


def complete(result: dict[str, Any]) -> None:
    global _status, _detail, _last_result, _finished_at
    with _lock:
        _status = "completed"
        _detail = "done"
        _last_result = result
        _finished_at = time.time()


def request_cancel() -> bool:
    """Signal a running indexer to stop. Returns False if nothing was running."""
    with _lock:
        if _status != "running":
            return False
    _cancel_event.set()
    return True


def cancel_requested() -> bool:
    return _cancel_event.is_set()


def mark_cancelled() -> None:
    global _status, _detail, _finished_at
    _cancel_event.clear()
    with _lock:
        _status = "cancelled"
        _detail = "Cancelled by user"
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
            "current_file": _current_file,
            "total_files": _total_files,
            "files_done": _files_done,
        }
