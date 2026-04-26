# Local Semantic Video & Photo Search

This project is a local semantic search engine for photos and MP4 clips using CLIP embeddings and FAISS similarity search, built as the Duke CS 372 Final Project.

## What it Does

This application provides a **proof-of-concept local semantic search** for multimedia. Users can naturally query their local image and video libraries without relying on cloud processing. Media processing (sampling video frames at ~1 FPS and generating CLIP embeddings) and exact cosine similarity searches happen entirely locally via Python and FAISS.

## Quick Start

1. Install environment using `mamba env create -f environment.yml` and `conda activate video-semantic-search`.
2. Optional: copy [`backend/.env.example`](backend/.env.example) to `backend/.env` to override CLIP model or paths (see [SETUP.md](SETUP.md)).
3. Start the FastAPI backend: `cd backend && uvicorn app.main:app --reload`.
4. Start the Vite React client: `cd frontend && npm install && npm run dev`.
5. Run `POST /index` via the UI or `curl` to construct the local FAISS index.

On Windows, after conda is on your PATH, you can optionally use [`start-dev.bat`](start-dev.bat) from the repo root to open two terminals (backend + frontend); edit `CONDA_BASE` inside the file if your install is not `%USERPROFILE%\miniforge3`.

For detailed setup instructions and prerequisites (like NVIDIA GPU driver compatibility), please see [SETUP.md](SETUP.md).

## Video Links

Replace the bracketed placeholders with your hosted URLs before the final Gradescope submission (course guidelines may require a specific host).

- **Demo video (non-specialist, no code):** paste your published URL here before submit
- **Technical walkthrough (code + ML + contributions):** paste your published URL here before submit

## Evaluation

**Throughput and latency (reproduce on your machine).** With a built index under `backend/database/`, from the repo root:

```bash
cd backend
python ../scripts/benchmark_search.py
python ../scripts/benchmark_index.py
```

`benchmark_search.py` prints `ntotal`, **mean / p50 / p95** end-to-end search latency (CLIP text encode + FAISS top-k) and approximate QPS. `benchmark_index.py` prints images/videos indexed, total embeddings, wall time, and **embeddings/sec** for a full rebuild. Record GPU model and driver (`nvidia-smi`) next to your numbers for the write-up.

**Demo retrieval benchmark.** After indexing the optional demo corpus (`python scripts/fetch_demo_dataset.py` then index `data/demo_corpus`), use the app **Benchmarks** tab **Run demo retrieval test** or `POST /benchmarks/demo-retrieval`. Test cases are defined in [`backend/benchmarks/demo_retrieval.json`](backend/benchmarks/demo_retrieval.json); note **top-k hit rate** (whether the expected asset appears in the top-k results for each labeled query) in your report.

**Design tradeoffs** (flat FAISS, concurrency, sampling): see [DESIGN.md](DESIGN.md).

## Individual Contributions

**Solo project:** Michael — sole author (entire design, implementation, evaluation, and documentation).

---

**Course:** Duke CS 372 — Introduction to Applied Machine Learning Spring 2026. See course policies for reuse.
