#!/usr/bin/env python3
"""
Measure search latency (CLIP text encode + FAISS search) on the loaded index.

Run from repo root with conda env active:

  cd backend && python ../scripts/benchmark_search.py
"""

from __future__ import annotations

import argparse
import os
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))
os.chdir(BACKEND)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=50, help="Total query repetitions")
    parser.add_argument("--top-k", type=int, default=10, dest="top_k")
    args = parser.parse_args()

    from app.services.clip_service import get_clip_service
    from app.services.faiss_store import get_faiss_store

    clip = get_clip_service()
    store = get_faiss_store()
    if store.is_corrupt:
        raise SystemExit("Index is corrupt or missing; run POST /index first.")
    n = len(store.metadata)
    if n == 0:
        raise SystemExit("Index is empty; run POST /index first.")

    queries = [
        "a mountain bike jump in the woods",
        "a person walking on the beach",
        "a dog playing",
        "sunset over water",
        "city skyline at night",
    ]
    times: list[float] = []
    for i in range(args.iterations):
        q = queries[i % len(queries)]
        t0 = time.perf_counter()
        qv = clip.encode_text([q])[0]
        store.search(qv, args.top_k)
        times.append(time.perf_counter() - t0)

    times.sort()
    p50 = statistics.median(times)
    p95 = times[int(0.95 * (len(times) - 1))]
    mean = statistics.fmean(times)

    print(f"ntotal={n}  iterations={args.iterations}  top_k={args.top_k}")
    print(f"latency_s: mean={mean:.6f}  p50={p50:.6f}  p95={p95:.6f}")
    print(f"qps (approx): {1.0 / mean:.2f}")


if __name__ == "__main__":
    main()
