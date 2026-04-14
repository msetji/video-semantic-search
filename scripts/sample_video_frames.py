#!/usr/bin/env python3
"""
Extract ~1 frame per second from an MP4 into a folder (JPEG). Uses shared logic
from the backend video sampler for consistency with indexing.

  python scripts/sample_video_frames.py input.mp4 ./out_frames
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.video_sampling import iter_frames_one_fps  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Sample 1 FPS frames from MP4 to JPEG files")
    parser.add_argument("video", type=Path, help="Input .mp4 path")
    parser.add_argument("out_dir", type=Path, help="Output directory for frames")
    parser.add_argument(
        "--max-frames",
        type=int,
        default=None,
        help="Optional cap on number of frames written",
    )
    args = parser.parse_args()
    if not args.video.is_file():
        raise SystemExit(f"Video not found: {args.video}")
    args.out_dir.mkdir(parents=True, exist_ok=True)

    for i, (t_sec, pil) in enumerate(iter_frames_one_fps(args.video, max_frames=args.max_frames)):
        name = f"frame_{i:05d}_t{t_sec:06.2f}s.jpg"
        out = args.out_dir / name
        pil.save(out, format="JPEG", quality=92)
        print(out)

    print("Done.")


if __name__ == "__main__":
    main()
