"""
Batch timing test: run iter_frames_one_fps over many videos and report aggregate stats.

Usage:
  python scripts/dev/test_batch_timing.py path/to/video/folder [max_videos]
"""
import sys
import time
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "backend"))

import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

from app.services.video_sampling import iter_frames_one_fps

folder = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
max_vids = int(sys.argv[2]) if len(sys.argv) > 2 else 20

videos = (
    sorted(folder.rglob("*.MP4"))
    + sorted(folder.rglob("*.mp4"))
    + sorted(folder.rglob("*.MOV"))
    + sorted(folder.rglob("*.mov"))
)
videos = videos[:max_vids]

print(f"\nProcessing {len(videos)} videos...\n")
t0_all = time.perf_counter()
total_frames = 0
total_ms = 0.0

for v in videos:
    t0 = time.perf_counter()
    frames = list(iter_frames_one_fps(v, max_frames=10))
    ms = (time.perf_counter() - t0) * 1000
    total_frames += len(frames)
    total_ms += ms
    print(f"  {v.name}: {len(frames)} frames in {ms:.0f}ms  ({ms/max(len(frames),1):.0f}ms/frame)")

total_s = time.perf_counter() - t0_all
print(f"\n{'='*60}")
print(f"Total: {total_frames} frames from {len(videos)} videos in {total_s:.1f}s")
print(f"Average: {total_ms/max(len(videos),1):.0f}ms/video, {total_ms/max(total_frames,1):.0f}ms/frame")
print(f"Throughput: {total_frames/total_s:.1f} frames/sec")
