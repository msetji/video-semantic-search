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
    
    p = Path(user_provided_relative_path)
    if p.is_absolute():
        return p.resolve()
        
    return (resolved_media_root / p).resolve()


def encoded_static_url_path_for_media_relative_path(absolute_posix_path: str) -> str:
    return "/media?path=" + quote(absolute_posix_path)
