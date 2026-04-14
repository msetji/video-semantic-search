from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

import numpy as np
from PIL import Image

from app.config import settings
from app.services.clip_service import get_clip_service
from app.services.faiss_store import get_faiss_store
from app.services.media_paths import resolve_scan_root_under_media_directory
from app.services.media_scan import relative_under_media, scan_media
from app.services.video_sampling import iter_frames_one_fps

logger = logging.getLogger(__name__)


def _metadata_record_for_image_file(
    absolute_image_path: Path,
    media_root_for_relative_paths: Path,
) -> dict:
    return {
        "path": relative_under_media(absolute_image_path, media_root_for_relative_paths),
        "kind": "image",
        "time_sec": None,
    }


def _metadata_record_for_video_frame(
    absolute_video_path: Path,
    media_root_for_relative_paths: Path,
    timestamp_seconds: float,
) -> dict:
    return {
        "path": relative_under_media(absolute_video_path, media_root_for_relative_paths),
        "kind": "video",
        "time_sec": float(timestamp_seconds),
    }


def rebuild_index(
    root_relative: str | None = None,
    progress_callback: Callable[[int], None] | None = None,
) -> dict:
    root = resolve_scan_root_under_media_directory(settings.media_root, root_relative)
    media_root = settings.media_root.resolve()
    clip = get_clip_service()
    store = get_faiss_store()

    cap = settings.max_frames_per_video
    images, videos = scan_media(root)
    meta: list[dict] = []
    vectors: list[np.ndarray] = []

    def report_current_embedding_count() -> None:
        if progress_callback:
            progress_callback(len(vectors))

    for img_path in images:
        try:
            pil = Image.open(img_path).convert("RGB")
        except OSError as e:
            logger.warning("Skip image %s: %s", img_path, e)
            continue
        emb = clip.encode_images([pil])
        vectors.append(emb)
        meta.append(_metadata_record_for_image_file(img_path, media_root))
        report_current_embedding_count()

    for vid_path in videos:
        try:
            for t_sec, pil in iter_frames_one_fps(vid_path, max_frames=cap):
                emb = clip.encode_images([pil])
                vectors.append(emb)
                meta.append(
                    _metadata_record_for_video_frame(vid_path, media_root, float(t_sec))
                )
                report_current_embedding_count()
        except Exception as e:  # noqa: BLE001
            logger.warning("Skip video %s: %s", vid_path, e)
            continue

    if not vectors:
        dim = clip.embedding_dim
        store.replace(np.zeros((0, dim), dtype=np.float32), [])
    else:
        all_vec = np.vstack(vectors).astype(np.float32)
        store.replace(all_vec, meta)
    store.save()

    return {
        "root": str(root),
        "images_indexed": len(images),
        "videos_indexed": len(videos),
        "embeddings": len(meta),
    }
