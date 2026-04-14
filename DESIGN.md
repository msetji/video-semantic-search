# Engineering notes (CS 372)

This document states **scope and limitations** deliberately. The project is an **end-to-end proof of concept** for local CLIP-based retrieval—not a production search platform.

## What this system is

- A **single-machine**, **local-only** pipeline: media on disk → full re-index on demand → text query → cosine similarity via FAISS.
- **Local storage** is a **course constraint** (privacy, no cloud upload), with tradeoffs: no multi-user auth, no shared index across machines, no managed hosting story.

## Search: FAISS `IndexFlatIP`

- Embeddings are **L2-normalized**; **inner product** equals **cosine similarity**.
- `IndexFlatIP` is **exact** but **O(n)** per query over `ntotal`. Appropriate for course-scale corpora (thousands to low millions of vectors depending on hardware), not billion-vector production loads.
- **Approximate** indices (IVF, PQ, HNSW) are the usual next step when `n` grows; they trade recall/latency for sublinear structure. We do **not** ship them in v1; flat index keeps the implementation simple and exact.

## GPU: PyTorch CLIP vs FAISS

- **CLIP** inference benefits strongly from GPU for batch encoding.
- **FAISS GPU** search helps more as `n` grows; for small `n`, CPU search can be competitive. **Measure** on your hardware (see `scripts/benchmark_search.py`); do not assume GPU is always faster.

## Indexing model

- **`POST /index` performs a full rebuild** of the scanned subtree: every image is re-embedded; every video is sampled at **~1 FPS** up to **`MAX_FRAMES_PER_VIDEO`** (default **7200** ≈ 2 hours at 1 FPS), then embeddings are written.
- **Incremental updates** (add one file without re-embedding everything) are **out of scope** for the current deadline; they are natural future work.
- **1 FPS sampling** bounds VRAM and index size by avoiding dense frame decoding; **4K** decoding is still CPU/GPU expensive—benchmark on your clips.

## Persistence: SQLite + FAISS

- Metadata lives in **`metadata.sqlite`** with row ids **`0 .. ntotal-1`** aligned with FAISS vector order.
- Saves use **temporary files** (`*.new`) and **`os.replace`** to reduce torn writes. On load, **`ntotal` must match** the SQLite row count or the index is treated as **corrupt** (HTTP 503 on search until a successful re-index).
- Legacy **`metadata.json`** is **migrated once** to SQLite if row counts match the FAISS index (then prefer SQLite only).

## Concurrency

- A **global lock** serializes indexing work. **Concurrent `POST /index` with `run_in_background: true`** returns **409** if a job is already **running** (reserved via `index_state`).
- Synchronous **`POST /index`** returns **503** if a background index is **running**; otherwise it **blocks** until it acquires the lock (so it waits if another synchronous indexer holds it).
- **`GET /index/status`** reflects **in-memory** state only and **resets on server restart**.

## Frontend

- The React app is a **minimal client** for calling the API and displaying results; it is **not** the primary research contribution.
