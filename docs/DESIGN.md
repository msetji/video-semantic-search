# Engineering notes (CS 372)

This document states **scope and limitations** deliberately. The project is an **end-to-end proof of concept** for local CLIP-based retrieval—not a production search platform.

## What this system is

- A **single-machine**, **local-only** pipeline: media on disk → `POST /index` on demand → text query → cosine similarity via FAISS.
- **Local storage** is a **course constraint** (privacy, no cloud upload), with tradeoffs: no multi-user auth, no shared index across machines, no managed hosting story.

## Search: FAISS `IndexFlatIP`

- Embeddings are **L2-normalized**; **inner product** equals **cosine similarity**.
- `IndexFlatIP` is **exact** but **O(n)** per query over `ntotal`. Appropriate for course-scale corpora (thousands to low millions of vectors depending on hardware), not billion-vector production loads.
- **Approximate** indices (IVF, PQ, HNSW) are the usual next step when `n` grows; they trade recall/latency for sublinear structure. We do **not** ship them in v1; flat index keeps the implementation simple and exact.

## GPU: PyTorch CLIP vs FAISS

- **CLIP** inference benefits strongly from GPU for batch encoding.
- **FAISS GPU** search helps more as `n` grows; for small `n`, CPU search can be competitive. **Measure** on your hardware (see `scripts/benchmark_search.py`); do not assume GPU is always faster.

## Indexing model

- **Per request, `POST /index` fully re-encodes the requested scan root(s)**: under each root, every image is re-embedded, and every video is sampled at **~1 FPS** up to **`MAX_FRAMES_PER_VIDEO`** (default **7200** ≈ 2 hours at 1 FPS), then the new vectors for that scan replace the previous embeddings for those paths in the FAISS store.
- **Cumulative / merged index (default `replace_entire_index: false`):** embeddings for paths *outside* the current scan (other folders indexed earlier) are **kept**. Send **`replace_entire_index: true`** to drop the whole index and replace it with only this run. This is **not** a “patch one new file in O(1)” update—re-scanning a subtree re-encodes that subtree.
- **True single-file / hot incremental add** (new file arrives, embed only that file with no rescan) is **out of scope** for the current deadline; it is natural future work.
- **1 FPS sampling** bounds VRAM and index size; **4K** decoding is still expensive—benchmark on your clips.

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
