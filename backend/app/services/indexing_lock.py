"""Serialize indexing work across threads (sync /index and background /index)."""

import threading

INDEXING_LOCK = threading.Lock()
