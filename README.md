# Local Semantic Video & Photo Search

This project is a local semantic search engine for photos and MP4 clips using CLIP embeddings and FAISS similarity search, built as the Duke CS 372 Final Project.

## What it Does

This application provides a **proof-of-concept local semantic search** for multimedia. Users can naturally query their local image and video libraries without relying on cloud processing. Media processing (sampling video frames at ~1 FPS and generating CLIP embeddings) and exact cosine similarity searches happen entirely locally via Python and FAISS.

## Quick Start

1. Install environment using `mamba env create -f environment.yml` and `conda activate video-semantic-search`.
2. Start the FastAPI backend: `cd backend && uvicorn app.main:app --reload`.
3. Start the Vite React client: `cd frontend && npm install && npm run dev`.
4. Run `POST /index` via the UI or `curl` to construct the local FAISS index.

For detailed setup instructions and prerequisites (like NVIDIA GPU driver compatibility), please see [SETUP.md](SETUP.md).

## Video Links

- Demo Video: [Insert link here]
- Technical Walkthrough: [Insert link here]

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

See [`ERROR_ANALYSIS.md`](ERROR_ANALYSIS.md) for screenshots, detailed analysis, and proposed mitigations.

For scope, concurrency, and hardware tradeoffs, see [DESIGN.md](DESIGN.md).

## Individual Contributions

| Team member | NetID | Primary contributions |
|-------------|-------|-------------------------|
| Michael Setji | mps69 | **Backend core:** initial FastAPI layout, `environment.yml`, and service/module structure. **Indexing:** batched CLIP encoding, threaded image/video prefetch, progress reporting, cancel path, merge vs full-replace index logic (`indexer.py`, `index.py`, `index_state.py`). **GPU / performance:** FP16 autocast, optional FAISS-GPU search path, VRAM cleanup after indexing (`clip_service.py`, `faiss_store.py`). **Benchmarks API:** search latency + random / gibberish / random-unit baselines, demo retrieval spec (`benchmarks.py`, `search_benchmark.py`, `demo_retrieval_benchmark.py`). **Infra:** indexing lock, corrupt-index handling, SQLite + FAISS atomic saves, library/logs routes. |
| Kabir Gupta | kg331 | **Frontend UX:** About page with project summary, main **tab navigation** across Search / Library / Benchmarks / Logs / About, and **demo screenshot** evaluation screenshots integration (`frontend/src/components/About.tsx`, `App.tsx`). **Documentation & submission (with partner):** README Evaluation / qualitative sections, `ERROR_ANALYSIS.md`, and `SELF_ASSESSMENT.md`—split editing/review with Michael as needed for accuracy. **Reviews:** UI changes merged via PR `kabir-changes1`.  **GPU / performance:** CUDA CLIP inference timing implementation |

---
**Course:** Duke CS 372 — Introduction to Applied Machine Learning Spring 2026. See course policies for reuse.