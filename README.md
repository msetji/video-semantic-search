# Local Semantic Video & Photo Search

**Proof-of-concept** local semantic search for photos and MP4 clips using **CLIP** embeddings and **FAISS** similarity search, with a **FastAPI** backend and a **minimal React + TypeScript + Tailwind** UI (the UI is for demo and querying—not the core research contribution). Media stays on disk under `data/`; the API serves files read-only and persists vectors under `backend/database/`.

**Course:** Duke CS 372 — Final Project (due April 26, 2026).

- Install and run: [SETUP.md](SETUP.md)
- **Scope, limitations, and concurrency:** [DESIGN.md](DESIGN.md)

## Individual Contributions

Fill in before submission:

| Team member | NetID | Primary contributions |
|-------------|-------|-------------------------|
| Partner 1   |       |                       |
| Partner 2   |       |                       |

## Repository layout

- `backend/` — FastAPI app (`app/`), CLIP + FAISS indexing, static `/media` mount
- `frontend/` — Vite React client; search bar and result grid
- `scripts/` — `baseline_clip.py`, `sample_video_frames.py`, `benchmark_index.py`, `benchmark_search.py`
- `data/` — Place or symlink media here (not committed)

## Results / benchmarks

For the write-up, run the benchmark scripts (see [SETUP.md](SETUP.md) § Benchmarks) and record GPU model, CUDA version, `ntotal`, and latency/throughput tables.

## License

Course project — see course policies for reuse.
