from pathlib import Path

from app.services.media_scan import scan_media


def test_scan_media_collects_raster_images_and_mp4_recursively(tmp_path: Path) -> None:
    root = tmp_path / "root"
    nested = root / "nested"
    nested.mkdir(parents=True)
    (root / "top.jpg").write_bytes(b"")
    (nested / "inner.png").write_bytes(b"")
    (nested / "clip.mp4").write_bytes(b"")
    (root / "ignored.txt").write_bytes(b"")

    images, videos = scan_media(root)

    assert sorted(images) == sorted([root / "top.jpg", nested / "inner.png"])
    assert videos == [nested / "clip.mp4"]


def test_scan_media_returns_empty_lists_when_root_missing(tmp_path: Path) -> None:
    missing = tmp_path / "nope"
    images, videos = scan_media(missing)
    assert images == []
    assert videos == []
