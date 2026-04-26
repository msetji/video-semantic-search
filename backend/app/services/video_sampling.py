"""
Sample video frames at ~1 frame per second.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Iterator
from pathlib import Path

import cv2
from PIL import Image

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# NVDEC probe via PyAV + conda-forge FFmpeg cuvid decoders.
# ---------------------------------------------------------------------------
_NVDEC_CODECS: frozenset[str] = frozenset()
try:
    import av as _av
    _cuvid = frozenset(c for c in _av.codec.codecs_available if c.endswith("_cuvid"))
    if _cuvid:
        _NVDEC_CODECS = _cuvid
        logger.info("NVDEC: ENABLED — cuvid codecs available: %s", sorted(_cuvid))
    else:
        logger.warning("NVDEC: DISABLED — PyAV loaded but no cuvid codecs found")
except ImportError:
    logger.warning("NVDEC: DISABLED — PyAV not installed (conda install -c conda-forge av)")


def iter_frames_one_fps(
    video_path: Path,
    *,
    max_frames: int | None = None,
) -> Iterator[tuple[float, Image.Image]]:
    """
    Yield (time_sec, RGB PIL Image) at approximately one frame per second.

    NVDEC path  — decodes only I-frames via PyAV/cuvid; each I-frame in DJI
                  footage is ~1 s apart, so this gives the same ~1 fps coverage
                  while skipping all P/B frame decode entirely.
    OpenCV path — stride sampling with cap.grab() for non-sampled frames.
    """
    if _NVDEC_CODECS:
        try:
            yield from _iter_pyav_nvdec(video_path, max_frames=max_frames)
            return
        except Exception as exc:
            logger.warning(
                "NVDEC failed for %s (%s) — falling back to OpenCV",
                video_path.name, exc,
            )
    yield from _iter_opencv(video_path, max_frames=max_frames)


def _iter_pyav_nvdec(
    video_path: Path,
    *,
    max_frames: int | None = None,
) -> Iterator[tuple[float, Image.Image]]:
    """
    Decode keyframes via NVDEC using PyAV 16's CodecContext.create() API.

    PyAV 16 does NOT support av.open(codec=...) or reassigning stream.codec_context.
    The working approach (validated via scripts/dev/probe_nvdec.py) is:
      1. Open the container with the SOFTWARE decoder to drive demuxing/seeking.
      2. Create a SEPARATE hw CodecContext from av.codec.Codec(hw_name, 'r').
      3. Copy width/height/extradata from the sw context to the hw context.
      4. Open the hw context and feed demuxed packets into it directly.

    This routes actual pixel decoding through NVDEC while relying on FFmpeg's
    container/demux layer (which has no WDAC issues) for the transport layer.
    """
    import av

    t_open = time.perf_counter()

    # Step 1 — probe metadata using software context (fast, no GPU)
    with av.open(str(video_path)) as probe:
        vs = probe.streams.video[0]
        fps    = float(vs.average_rate or vs.guessed_rate or 30)
        codec  = vs.codec_context.name          # 'hevc', 'h264', …
        width  = vs.codec_context.width
        height = vs.codec_context.height
        total  = vs.frames or int((vs.duration or 0) * float(vs.time_base) * fps)

    hw_codec_name = f"{codec}_cuvid"
    if hw_codec_name not in _NVDEC_CODECS:
        raise RuntimeError(f"No cuvid decoder for codec {codec!r}")

    # Step 2 — build hardware CodecContext
    try:
        hw_codec_obj = _av.codec.Codec(hw_codec_name, "r")
        hw_ctx = _av.codec.CodecContext.create(hw_codec_obj)
    except Exception as exc:
        raise RuntimeError(f"Could not create hw CodecContext for {hw_codec_name}: {exc}") from exc

    # Step 3 — open container again (sw decoder drives the demuxer)
    #           and copy stream parameters into hw_ctx before opening it
    container = av.open(str(video_path))
    try:
        vs = container.streams.video[0]
        sw_ctx = vs.codec_context

        hw_ctx.width  = sw_ctx.width
        hw_ctx.height = sw_ctx.height
        if sw_ctx.extradata:
            hw_ctx.extradata = sw_ctx.extradata
        hw_ctx.open()

        t_opened = time.perf_counter()
        logger.info(
            "Video %s: codec=%s res=%dx%d fps=%.1f total_frames=%d duration=%.0fs"
            " [NVDEC/%s, keyframes-only] init=%.0fms",
            video_path.name, codec, width, height, fps,
            total, total / fps if fps else 0, hw_codec_name,
            (t_opened - t_open) * 1000,
        )

        # Step 4 — demux via sw container, decode via hw_ctx
        emitted       = 0
        last_time     = -1.0
        t_decode_sum  = 0.0

        for packet in container.demux(vs):
            if not packet.is_keyframe:
                continue

            # time_base is on the *stream*, not the hw_ctx
            t_d = time.perf_counter()
            frames = hw_ctx.decode(packet)
            t_decode_sum += time.perf_counter() - t_d

            for frame in frames:
                if frame.pts is None:
                    continue
                time_sec = float(frame.pts * vs.time_base)
                if time_sec - last_time < 1.0:
                    continue
                yield time_sec, frame.to_image()
                last_time = time_sec
                emitted  += 1
                if max_frames is not None and emitted >= max_frames:
                    return

        # Some short clips can expose no usable keyframes through this fast path.
        # Signal caller to use OpenCV stride sampling instead of silently returning 0 frames.
        if emitted == 0:
            raise RuntimeError(
                f"NVDEC keyframe path emitted 0 frames for {video_path.name}; fallback required"
            )

    finally:
        container.close()
        logger.info(
            "Video %s: emitted=%d frames, pure_hw_decode=%.0fms, total=%.0fms",
            video_path.name, emitted,
            t_decode_sum * 1000,
            (time.perf_counter() - t_open) * 1000,
        )


def _iter_opencv(
    video_path: Path,
    *,
    max_frames: int | None = None,
) -> Iterator[tuple[float, Image.Image]]:
    t_open = time.perf_counter()
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        logger.warning("Could not open video: %s", video_path)
        return
    t_opened = time.perf_counter()

    fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
    if fps <= 1e-6:
        fps = 30.0

    fourcc_int = int(cap.get(cv2.CAP_PROP_FOURCC))
    fourcc = "".join(chr((fourcc_int >> (8 * i)) & 0xFF) for i in range(4)).strip("\x00").strip()
    width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total  = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    logger.info(
        "Video %s: codec=%s res=%dx%d fps=%.1f duration=%.0fs total_frames=%d [OpenCV] open=%.0fms",
        video_path.name, fourcc, width, height, fps,
        total / fps if fps else 0, total,
        (t_opened - t_open) * 1000,
    )

    frame_interval = max(1, int(round(fps)))
    idx = 0
    emitted = 0
    t_decode_total = 0.0
    try:
        while True:
            if idx % frame_interval == 0:
                t_d = time.perf_counter()
                ok, frame = cap.read()
                t_decode_total += time.perf_counter() - t_d
                if not ok:
                    break
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                yield idx / fps, Image.fromarray(rgb)
                emitted += 1
                if max_frames is not None and emitted >= max_frames:
                    break
            else:
                if not cap.grab():
                    break
            idx += 1
    finally:
        cap.release()
        logger.info(
            "Video %s (OpenCV): emitted=%d frames, pure_decode=%.0fms, open=%.0fms",
            video_path.name, emitted,
            t_decode_total * 1000,
            (t_opened - t_open) * 1000,
        )
