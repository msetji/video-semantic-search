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

    max_frames = settings.max_frames_per_video
    images, videos = scan_media(root)
    meta: list[dict] = []
    vectors: list[np.ndarray] = []

    BATCH_SIZE = 128
    batch_pils: list[Image.Image] = []
    batch_meta: list[dict] = []

    def flush_batch() -> None:
        if not batch_pils:
            return
        embeddings = clip.encode_images(batch_pils, batch_size=BATCH_SIZE)
        vectors.append(embeddings)
        
        start_idx = len(meta)
        meta.extend(batch_meta)
        end_idx = len(meta)
        
        for i in range(start_idx + 1, end_idx + 1):
            logger.info("Progress: Finished embedding %d", i)
            
        if progress_callback:
            progress_callback(end_idx)
            
        batch_pils.clear()
        batch_meta.clear()

    logger.info("Starting indexing. Found %d images and %d videos.", len(images), len(videos))

    for image_file_path in images:
        logger.info("Processing image: %s", image_file_path.name)
        try:
            pil = Image.open(image_file_path).convert("RGB")
        except OSError as e:
            logger.warning("Skip image %s: %s", image_file_path, e)
            continue
            
        batch_pils.append(pil)
        batch_meta.append(_metadata_record_for_image_file(image_file_path, media_root))
        if len(batch_pils) >= BATCH_SIZE:
            flush_batch()

    for video_file_path in videos:
        logger.info("Processing video: %s", video_file_path.name)
        try:
            for timestamp_sec, pil in iter_frames_one_fps(video_file_path, max_frames=max_frames):
                batch_pils.append(pil)
                batch_meta.append(
                    _metadata_record_for_video_frame(video_file_path, media_root, float(timestamp_sec))
                )
                if len(batch_pils) >= BATCH_SIZE:
                    flush_batch()
        except Exception as e:  # noqa: BLE001
            logger.warning("Skip video %s: %s", video_file_path, e)
            continue

    flush_batch()

    if not vectors:
        dim = clip.embedding_dim
        store.replace(np.zeros((0, dim), dtype=np.float32), [])
        logger.info("No media found. Cleared index.")
    else:
        all_vec = np.vstack(vectors).astype(np.float32)
        store.replace(all_vec, meta)
        logger.info("Saved %d embeddings to the index.", len(vectors))
    store.save()

    logger.info("Indexing completed successfully.")

    return {
        "root": str(root),
        "images_indexed": len(images),
        "videos_indexed": len(videos),
        "embeddings": len(meta),
    }
