from pathlib import Path

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
VIDEO_EXTENSIONS = {".mp4"}


def scan_media(root: Path) -> tuple[list[Path], list[Path]]:
    images: list[Path] = []
    videos: list[Path] = []
    root = root.resolve()
    if not root.is_dir():
        return images, videos
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        ext = path.suffix.lower()
        if ext in IMAGE_EXTENSIONS:
            images.append(path)
        elif ext in VIDEO_EXTENSIONS:
            videos.append(path)
    images.sort()
    videos.sort()
    return images, videos


def relative_under_media(path: Path, media_root: Path) -> str:
    return path.resolve().relative_to(media_root.resolve()).as_posix()
