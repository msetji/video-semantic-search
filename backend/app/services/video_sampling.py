"""
Sample video frames at ~1 frame per second.

Decimating dense frame streams keeps batch sizes bounded and avoids loading
full-resolution frame sequences into GPU memory at once (VRAM-friendly).
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from pathlib import Path

import cv2
from PIL import Image

logger = logging.getLogger(__name__)


def iter_frames_one_fps(
    video_path: Path,
    *,
    max_frames: int | None = None,
) -> Iterator[tuple[float, Image.Image]]:
    """
    Yield (time_sec, RGB PIL Image) at approximately one frame per second.

    Uses stride sampling: take one frame every `round(fps)` frames so that
    spacing tracks native FPS (e.g. 30 fps -> every 30th frame ~= 1s).
    """
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        logger.warning("Could not open video: %s", video_path)
        return
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
    if fps <= 1e-6:
        fps = 30.0
    frame_interval = max(1, int(round(fps)))
    idx = 0
    emitted = 0
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if idx % frame_interval == 0:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil = Image.fromarray(rgb)
                time_sec = idx / fps
                yield time_sec, pil
                emitted += 1
                if max_frames is not None and emitted >= max_frames:
                    break
            idx += 1
    finally:
        cap.release()
