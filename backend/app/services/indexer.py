from __future__ import annotations

import logging
import time
from collections import deque
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from functools import partial
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from torchvision import transforms

from app.config import settings
from app.exceptions import IndexCancelledError
from app.services import index_state
from app.services.clip_service import get_clip_service
from app.services.faiss_store import get_faiss_store
from app.services.media_paths import resolve_scan_root_under_media_directory
from app.services.media_scan import relative_under_media, scan_media
from app.services.video_sampling import iter_frames_one_fps

logger = logging.getLogger(__name__)

_IO_THREADS = 16
_PREFETCH = 512  # images loaded ahead of the GPU batch

# HuggingFace's CLIPProcessor is heavily GIL-locked.
# We replace it with PyTorch's native C++ optimized transforms.
fast_transform = transforms.Compose([
    transforms.Resize(224, interpolation=transforms.InterpolationMode.BICUBIC),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.48145466, 0.4578275, 0.40821073],
        std=[0.26862954, 0.26130258, 0.27577711]
    )
])


def _load_and_preprocess(path: Path) -> dict[str, torch.Tensor] | None:
    try:
        pil = Image.open(path).convert("RGB")
        return {"pixel_values": fast_transform(pil).unsqueeze(0)}
    except Exception as e:
        logger.warning("Skip image %s: %s", path, e)
        return None


def _preprocess_pil(pil: Image.Image) -> dict[str, torch.Tensor] | None:
    try:
        return {"pixel_values": fast_transform(pil).unsqueeze(0)}
    except Exception as e:
        logger.warning("Skip frame: %s", e)
        return None



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
    file_progress_callback: Callable[[str, int, int], None] | None = None,
) -> dict:
    root = resolve_scan_root_under_media_directory(settings.media_root, root_relative)
    media_root = settings.media_root.resolve()
    clip = get_clip_service()
    store = get_faiss_store()

    max_frames = settings.max_frames_per_video
    images, videos = scan_media(root)
    meta: list[dict] = []
    vectors: list[np.ndarray] = []

    total_files = len(images) + len(videos)
    files_done = 0

    BATCH_SIZE = 32
    batch_inputs: list[dict] = []
    batch_meta: list[dict] = []

    def flush_batch() -> None:
        if not batch_inputs:
            return
        batch_size = len(batch_inputs)
        t_encode = time.perf_counter()
        stacked = {k: torch.cat([item[k] for item in batch_inputs]) for k in batch_inputs[0]}
        embeddings = clip.encode_preprocessed(stacked)
        encode_ms = (time.perf_counter() - t_encode) * 1000

        vectors.append(embeddings)
        meta.extend(batch_meta)

        if progress_callback:
            progress_callback(len(meta))

        logger.info(
            "Encoded batch: %d items in %.0f ms — running total: %d embeddings",
            batch_size,
            encode_ms,
            len(meta),
        )
        batch_inputs.clear()
        batch_meta.clear()

    logger.info("Starting indexing. Found %d images and %d videos.", len(images), len(videos))
    t_start = time.perf_counter()

    load_fn = _load_and_preprocess

    with ThreadPoolExecutor(max_workers=_IO_THREADS) as pool:
        image_iter = iter(images)
        in_flight: deque[tuple[Future, Path]] = deque()

        for path in images[:_PREFETCH]:
            in_flight.append((pool.submit(load_fn, path), path))
        image_iter = iter(images[_PREFETCH:])

        while in_flight:
            if index_state.cancel_requested():
                logger.info("Cancellation detected — stopping after %d files.", files_done)
                raise IndexCancelledError()

            future, image_file_path = in_flight.popleft()
            try:
                next_path = next(image_iter)
                in_flight.append((pool.submit(load_fn, next_path), next_path))
            except StopIteration:
                pass

            logger.info("Processing image: %s", image_file_path.name)
            if file_progress_callback:
                file_progress_callback(image_file_path.name, files_done, total_files)
            files_done += 1

            inputs = future.result()
            if inputs is None:
                continue
            batch_inputs.append(inputs)
            batch_meta.append(_metadata_record_for_image_file(image_file_path, media_root))
            if len(batch_inputs) >= BATCH_SIZE:
                flush_batch()

        in_flight_videos: deque[tuple[Future, dict]] = deque()
        VIDEO_PREFETCH = 64

        def drain_video_tasks(target_length: int) -> None:
            while len(in_flight_videos) > target_length:
                future, meta_dict = in_flight_videos.popleft()
                res = future.result()
                if res is not None:
                    batch_inputs.append(res)
                    batch_meta.append(meta_dict)
                    if len(batch_inputs) >= BATCH_SIZE:
                        flush_batch()

        for video_file_path in videos:
            if index_state.cancel_requested():
                logger.info("Cancellation detected — stopping after %d files.", files_done)
                raise IndexCancelledError()

            logger.info("Processing video: %s", video_file_path.name)
            if file_progress_callback:
                file_progress_callback(video_file_path.name, files_done, total_files)
            try:
                for timestamp_sec, pil in iter_frames_one_fps(video_file_path, max_frames=max_frames):
                    frame_meta = _metadata_record_for_video_frame(video_file_path, media_root, float(timestamp_sec))
                    in_flight_videos.append((pool.submit(_preprocess_pil, pil), frame_meta))
                    drain_video_tasks(VIDEO_PREFETCH)
            except IndexCancelledError:
                raise
            except Exception as e:  # noqa: BLE001
                logger.warning("Skip video %s: %s", video_file_path, e)
            files_done += 1

        drain_video_tasks(0)

    flush_batch()

    if not vectors:
        dim = clip.embedding_dim
        store.replace(np.zeros((0, dim), dtype=np.float32), [])
        logger.warning("No media found under %s — index cleared.", root)
    else:
        all_vec = np.vstack(vectors).astype(np.float32)
        store.replace(all_vec, meta)
        logger.info("Saved %d embeddings to FAISS index.", len(meta))
    store.save()

    elapsed_s = time.perf_counter() - t_start
    logger.info(
        "Indexing complete in %.1f s — %d images, %d videos, %d total embeddings.",
        elapsed_s,
        len(images),
        len(videos),
        len(meta),
    )

    return {
        "root": str(root),
        "images_indexed": len(images),
        "videos_indexed": len(videos),
        "embeddings": len(meta),
    }
