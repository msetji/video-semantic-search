"""
Quick end-to-end test of video_sampling.iter_frames_one_fps.
Prints per-frame timing and total throughput.

Usage:
  python scripts/dev/test_sampling.py path/to/video.mp4 [max_frames]
"""
import sys
import time
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "backend"))

import logging

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

from app.services.video_sampling import iter_frames_one_fps

if len(sys.argv) < 2:
    print("Usage: python scripts/dev/test_sampling.py path/to/video [max_frames]")
    sys.exit(1)

path = Path(sys.argv[1])
max_f = int(sys.argv[2]) if len(sys.argv) > 2 else None

print(f"\nSampling: {path.name}  max_frames={max_f}\n")
t0 = time.perf_counter()
frames = []
for ts, img in iter_frames_one_fps(path, max_frames=max_f):
    elapsed = time.perf_counter() - t0
    print(f"  frame {len(frames)+1}: t={ts:.2f}s  size={img.size}  elapsed={elapsed*1000:.0f}ms")
    frames.append((ts, img))

total = time.perf_counter() - t0
print(f"\n{len(frames)} frames in {total*1000:.0f}ms  ({len(frames)/total:.1f} fps throughput)")
