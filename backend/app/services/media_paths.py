from __future__ import annotations

from pathlib import Path
from urllib.parse import quote


def resolve_scan_root_under_media_directory(
    media_root: Path,
    user_provided_relative_path: str | None,
) -> Path:
    resolved_media_root = media_root.resolve()
    if user_provided_relative_path is None or not user_provided_relative_path.strip():
        return resolved_media_root
    candidate = (resolved_media_root / user_provided_relative_path).resolve()
    if not candidate.is_relative_to(resolved_media_root):
        raise ValueError("path escapes media root")
    return candidate


def encoded_static_url_path_for_media_relative_path(relative_posix_path: str) -> str:
    path_segments = relative_posix_path.split("/")
    encoded_segments = [quote(segment) for segment in path_segments]
    return "/media/" + "/".join(encoded_segments)
