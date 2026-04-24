from pathlib import Path

import pytest

from app.services.media_paths import (
    encoded_static_url_path_for_media_relative_path,
    resolve_scan_root_under_media_directory,
)


def test_resolve_scan_root_returns_media_root_when_path_is_empty(tmp_path: Path) -> None:
    media_root = tmp_path / "data"
    media_root.mkdir()
    resolved = resolve_scan_root_under_media_directory(media_root, None)
    assert resolved == media_root.resolve()


def test_resolve_scan_root_returns_media_root_when_path_is_whitespace_only(
    tmp_path: Path,
) -> None:
    media_root = tmp_path / "data"
    media_root.mkdir()
    resolved = resolve_scan_root_under_media_directory(media_root, "   ")
    assert resolved == media_root.resolve()


def test_resolve_scan_root_accepts_nested_subdirectory_under_media_root(
    tmp_path: Path,
) -> None:
    media_root = tmp_path / "data"
    vacation = media_root / "vacation" / "2024"
    vacation.mkdir(parents=True)
    resolved = resolve_scan_root_under_media_directory(media_root, "vacation/2024")
    assert resolved == vacation.resolve()


def test_resolve_scan_root_rejects_escape_above_media_root(tmp_path: Path) -> None:
    media_root = tmp_path / "data"
    media_root.mkdir()
    with pytest.raises(ValueError, match="path escapes media root"):
        resolve_scan_root_under_media_directory(media_root, "..")


def test_resolve_scan_root_rejects_absolute_path_style_escape(tmp_path: Path) -> None:
    media_root = tmp_path / "data"
    media_root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    with pytest.raises(ValueError, match="path escapes media root"):
        resolve_scan_root_under_media_directory(media_root, "../outside")


def test_encoded_static_url_percent_encodes_path_segments() -> None:
    url = encoded_static_url_path_for_media_relative_path("my folder/clip#1.mp4")
    assert url.startswith("/media/")
    assert "my%20folder" in url
    assert "clip%231" in url
