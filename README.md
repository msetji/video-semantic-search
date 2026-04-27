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

### Inference timing (search path)

Latency is measured on the **same CLIP + FAISS code path** as live search.

**Primary method (recommended for this table):** open the app’s **Benchmarks** tab and run **Search latency + random baselines**, or call the API after indexing:

```bash
curl -s -X POST "http://127.0.0.1:8000/benchmarks/search" \
  -H "Content-Type: application/json" \
  -d '{"iterations": 40, "top_k": 12, "media_filter": "both", "seed": 42}' | python3 -m json.tool
```

Copy from the JSON: `ntotal`, `latency_mean_s`, `latency_p50_s`, `latency_p95_s`, `qps` (seconds → multiply by 1000 for ms below).

| Field | Your value |
|-------|------------|
| Hardware (CPU / GPU, RAM) | Ryzen 7 9850X, RTX5070 |
| CUDA / driver (if GPU) | CUDA Version: 13.1, Driver Version: 591.81 |
| Mean latency | 4.64 ms |
| p50 latency | 4.59 ms |
| p95 latency | 5.26 ms |
| Queries per second (`qps`) | 215.42 |


Implementation reference: `backend/app/services/search_benchmark.py`, `backend/app/api/benchmarks.py`, `backend/app/api/search.py`.

### Qualitative Results

The system performs well on concrete, descriptive queries. Example searches that return highly relevant results:

- `"airplane"` → retrieves frames of aircraft in flight, on runways, in hangars
- `"road"` → retrieves frames with roads during motion and still
- `"person"` → retrieves action frames of people

### Known Failure Modes

A structured error analysis is documented in [`ERROR_ANALYSIS.md`](ERROR_ANALYSIS.md). Key failure categories include:

1. **Abstract concepts** (e.g. `"love"`) — CLIP's embeddings are anchored to literal visual descriptions, not emotional interpretations.
2. **Spatial / relational queries** (e.g. `"cat on top of table"`) — the global ViT embedding discards spatial layout between objects.
3. **Negation** (e.g. `"person without hat"`) — contrastive training does not model logical negation, so it is effectively ignored.
4. **Fine-grained distinctions** (e.g. `"golden retriever"` vs `"labrador retriever"`) — noisy web captions conflate visually similar categories.
5. **OCR / text in images** — the vision encoder reads text as visual texture, not as characters.

See [`ERROR_ANALYSIS.md`](ERROR_ANALYSIS.md) for screenshot, detailed analysis, and proposed mitigations.

For scope, concurrency, and hardware tradeoffs, see [DESIGN.md](DESIGN.md).

## Individual Contributions

| Team member | NetID | Primary contributions |
|-------------|-------|-------------------------|
| Michael Setji | mps69 | **Backend core:** initial FastAPI layout, `environment.yml`, and service/module structure. **Indexing:** batched CLIP encoding, threaded image/video prefetch, progress reporting, cancel path, merge vs full-replace index logic (`indexer.py`, `index.py`, `index_state.py`). **GPU / performance:** FP16 autocast, optional FAISS-GPU search path, VRAM cleanup after indexing (`clip_service.py`, `faiss_store.py`). **Benchmarks API:** search latency + random / gibberish / random-unit baselines, demo retrieval spec (`benchmarks.py`, `search_benchmark.py`, `demo_retrieval_benchmark.py`). **Infra:** indexing lock, corrupt-index handling, SQLite + FAISS atomic saves, library/logs routes. |
| Kabir Gupta | kg331 | **Frontend UX:** About page with project summary, main **tab navigation** across Search / Library / Benchmarks / Logs / About, and **demo screenshot** evaluation screenshots integration (`frontend/src/components/About.tsx`, `App.tsx`). **Documentation & submission (with partner):** README Evaluation / qualitative sections, `ERROR_ANALYSIS.md`, and `SELF_ASSESSMENT.md`—split editing/review with Michael as needed for accuracy. **Reviews:** UI changes merged via PR `kabir-changes1`.  **GPU / performance:** CUDA CLIP inference timing implementation |

---
**Throughput and latency (reproduce on your machine).** With a built index under `backend/database/`, from the repo root:

```bash
cd backend
python ../scripts/benchmark_search.py
python ../scripts/benchmark_index.py
```

`benchmark_search.py` prints `ntotal`, **mean / p50 / p95** end-to-end search latency (CLIP text encode + FAISS top-k) and approximate QPS. `benchmark_index.py` prints images/videos indexed, total embeddings, wall time, and **embeddings/sec** for a full rebuild. Record GPU model and driver (`nvidia-smi`) next to your numbers for the write-up.

**Demo retrieval benchmark.** After indexing the optional demo corpus (`python scripts/fetch_demo_dataset.py` then index `data/demo_corpus`), use the app **Benchmarks** tab **Run demo retrieval test** or `POST /benchmarks/demo-retrieval`. Test cases are defined in [`backend/benchmarks/demo_retrieval.json`](backend/benchmarks/demo_retrieval.json); note **top-k hit rate** (whether the expected asset appears in the top-k results for each labeled query) in your report.

**Design tradeoffs** (flat FAISS, concurrency, sampling): see [DESIGN.md](DESIGN.md).
---

**Course:** Duke CS 372 — Introduction to Applied Machine Learning Spring 2026. See course policies for reuse.
