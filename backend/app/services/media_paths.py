from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote


def is_same_or_inside_directory(child_norm: str, root_norm: str) -> bool:
    """True if child_norm is root_norm or a subdirectory (Windows-safe normcase)."""
    c = os.path.normcase(child_norm)
    r = os.path.normcase(root_norm)
    return c == r or c.startswith(r + os.sep)


def resolve_scan_root_under_media_directory(
    media_root: Path,
    user_provided_relative_path: str | None,
) -> Path:
    resolved_media_root = media_root.resolve()
    if user_provided_relative_path is None or not user_provided_relative_path.strip():
        return resolved_media_root
    
    p = Path(user_provided_relative_path)
    if p.is_absolute():
        return p.resolve()
        
    return (resolved_media_root / p).resolve()


def encoded_static_url_path_for_media_relative_path(absolute_posix_path: str) -> str:
    return "/media?path=" + quote(absolute_posix_path)


def metadata_path_key_for_removal_matching(stored: str) -> str:
    """Normcase + normpath on POSIX-style path for stable equality / prefix checks."""
    raw = stored.strip()
    return os.path.normcase(os.path.normpath(Path(raw).as_posix()))


@dataclass(frozen=True)
class IndexMergeRemovalSpec:
    """Arguments for FaissStore.remove_paths before merging a new index run."""

    file_paths: frozenset[str]
    directory_prefix_keys: frozenset[str]
    remove_all_non_absolute_paths: bool


def index_merge_removal_spec(scan_root: Path, media_root: Path) -> IndexMergeRemovalSpec:
    """What to strip from the existing index before adding embeddings for scan_root."""
    s = scan_root.resolve()
    m = media_root.resolve()
    try:
        rel = s.relative_to(m)
        rel_posix = rel.as_posix()
        if rel_posix == ".":
            return IndexMergeRemovalSpec(
                frozenset(),
                frozenset(),
                remove_all_non_absolute_paths=True,
            )
        return IndexMergeRemovalSpec(
            frozenset(),
            frozenset({metadata_path_key_for_removal_matching(rel_posix)}),
            remove_all_non_absolute_paths=False,
        )
    except ValueError:
        root_key = metadata_path_key_for_removal_matching(str(s))
        return IndexMergeRemovalSpec(
            frozenset(),
            frozenset({root_key}),
            remove_all_non_absolute_paths=False,
        )
