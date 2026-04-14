from __future__ import annotations

import json
import logging
import os
import sqlite3
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE embedding_rows (
  id INTEGER PRIMARY KEY,
  path TEXT NOT NULL,
  kind TEXT NOT NULL,
  time_sec REAL
);
"""


def write_rows_file(sqlite_path: Path, rows: list[dict[str, Any]]) -> None:
    """Create or overwrite a SQLite file with embedding_rows (ids 0..n-1)."""
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(sqlite_path))
    try:
        conn.executescript("DROP TABLE IF EXISTS embedding_rows; " + _SCHEMA)
        conn.executemany(
            "INSERT INTO embedding_rows (id, path, kind, time_sec) VALUES (?,?,?,?)",
            [(i, r["path"], r["kind"], r["time_sec"]) for i, r in enumerate(rows)],
        )
        conn.commit()
    finally:
        conn.close()


def write_rows_atomic(sqlite_path: Path, rows: list[dict[str, Any]]) -> None:
    """Write metadata to sqlite_path atomically via temp file + os.replace."""
    tmp = sqlite_path.with_name(sqlite_path.name + ".tmp")
    if tmp.exists():
        tmp.unlink()
    write_rows_file(tmp, rows)
    os.replace(tmp, sqlite_path)


def read_rows(sqlite_path: Path) -> list[dict[str, Any]]:
    conn = sqlite3.connect(str(sqlite_path))
    try:
        cur = conn.execute(
            "SELECT id, path, kind, time_sec FROM embedding_rows ORDER BY id"
        )
        out: list[dict[str, Any]] = []
        for row_id, path, kind, time_sec in cur:
            if row_id != len(out):
                raise ValueError(f"non-contiguous row id {row_id}")
            out.append({"path": path, "kind": kind, "time_sec": time_sec})
        return out
    finally:
        conn.close()


def row_count(sqlite_path: Path) -> int:
    conn = sqlite3.connect(str(sqlite_path))
    try:
        (n,) = conn.execute("SELECT COUNT(*) FROM embedding_rows").fetchone()
        return int(n)
    finally:
        conn.close()


def load_legacy_json(path: Path) -> list[dict[str, Any]] | None:
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            return None
        return data
    except OSError:
        return None


def migrate_json_to_sqlite(
    legacy_json: Path, sqlite_path: Path, expected_n: int
) -> bool:
    """If legacy JSON row count matches FAISS ntotal, write SQLite and return True."""
    rows = load_legacy_json(legacy_json)
    if rows is None or len(rows) != expected_n:
        logger.warning(
            "Legacy metadata.json present but row count mismatch or invalid; skip migrate"
        )
        return False
    write_rows_atomic(sqlite_path, rows)
    logger.info("Migrated metadata.json to SQLite at %s", sqlite_path)
    return True
