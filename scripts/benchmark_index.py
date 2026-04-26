#!/usr/bin/env python3
"""
Time a full re-index (scan + CLIP encode + FAISS build + save) for a folder under MEDIA_ROOT.

Uses the same pipeline as POST /index. Run from repo root:

  cd backend && python ../scripts/benchmark_index.py
  cd backend && python ../scripts/benchmark_index.py --root subfolder
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))
os.chdir(BACKEND)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root",
        type=str,
        default=None,
        help="Optional path relative to MEDIA_ROOT (same as POST /index root_path)",
    )
    args = parser.parse_args()

    from app.services.indexer import rebuild_index

    t0 = time.perf_counter()
    stats = rebuild_index(args.root, replace_entire_index=True)
    elapsed = time.perf_counter() - t0
    emb = stats["embeddings"]
    rate = emb / elapsed if elapsed > 0 else 0.0
    print(f"root={stats['root']}")
    print(f"images={stats['images_indexed']}  videos={stats['videos_indexed']}  embeddings={emb}")
    print(f"wall_time_s={elapsed:.3f}  embeddings_per_s={rate:.2f}")


if __name__ == "__main__":
    main()
