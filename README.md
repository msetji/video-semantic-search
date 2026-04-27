# Local Semantic Video & Photo Search

## Project goal

**Research question:** *Can a single local pipeline—vision–language (CLIP) embeddings and approximate nearest-neighbor search (FAISS)—support interactive **open-vocabulary** semantic search over a user’s own photos and short videos in natural language, with acceptable latency and no cloud processing of that media?*

**What we deliver:** a Duke CS 372 end-to-end system that tests this by indexing sampled frames and stills and retrieving matches for text queries entirely on the user’s machine, then evaluating latency, realistic qualitative behavior, and known failure modes (see [Evaluation](#evaluation) and [docs/ERROR_ANALYSIS.md](docs/ERROR_ANALYSIS.md)).

## What it Does

The app is a **proof of concept** for the goal above. You write a text query; the system returns the most visually similar stills from your library. For video, frames are drawn at about **one per second**, embedded with CLIP, and stored in a FAISS index for cosine search against the query embedding; the stack is Python, PyTorch, and optional FAISS-GPU on the host—no media leaves your machine.

## Quick Start

1. Create and activate the conda environment: `mamba env create -f environment.yml` (or `conda env create -f environment.yml`) then `conda activate video-semantic-search`.
2. Optional: copy [`backend/.env.example`](backend/.env.example) to `backend/.env` to override CLIP model or paths (see [docs/SETUP.md](docs/SETUP.md)).
3. Start the FastAPI backend: `cd backend && uvicorn app.main:app --reload` (use `--host 0.0.0.0 --port 8000` for LAN access; details in [docs/SETUP.md](docs/SETUP.md)).
4. Start the Vite client: `cd frontend && npm install && npm run dev`.
5. Build the local index: use `POST /index` from the UI or `curl` after the server is up.

On Windows, with conda on your `PATH`, you can use [`start-dev.bat`](start-dev.bat) from the repo root to open two terminals (backend + frontend). Edit `CONDA_BASE` inside the file if your install is not `%USERPROFILE%\miniforge3`.

For prerequisites (GPU driver, Node 20+, optional demo corpus) and API details, see [docs/SETUP.md](docs/SETUP.md).

## Video Links

Course submission videos (view or download from Google Drive):

- **Demo video (non-specialist, no code):** https://drive.google.com/file/d/1qdX6NO7QlicbFS447Db6548D9n2l78O7/view?usp=sharing
- **Technical walkthrough (code, ML, contributions):** https://drive.google.com/file/d/14FjLW3-hY5hWTEYdJclc9H2wTf70J3l_/view?usp=sharing

## Evaluation

### Inference timing (search path)

Latency is measured on the **same CLIP + FAISS code path** as live search.

**Primary method (recommended for the table):** open the app’s **Benchmarks** tab and run **Search latency + random baselines**, or call the API after indexing:

```bash
curl -s -X POST "http://127.0.0.1:8000/benchmarks/search" \
  -H "Content-Type: application/json" \
  -d '{"iterations": 40, "top_k": 12, "media_filter": "both", "seed": 42}' | python3 -m json.tool
```

From the JSON, record `ntotal`, `latency_mean_s`, `latency_p50_s`, `latency_p95_s`, and `qps` (seconds → multiply by 1000 for ms in a table if needed).

**Example run (one team machine; replace with your hardware and measured JSON):**

| Field | Your value |
|-------|------------|
| Hardware (CPU / GPU, RAM) | Ryzen 7 9850X, RTX5070 |
| CUDA / driver (if GPU) | CUDA Version: 13.1, Driver Version: 591.81 |
| Mean latency | 4.64 ms |
| p50 latency | 4.59 ms |
| p95 latency | 5.26 ms |
| Queries per second (`qps`) | 215.42 |

Implementation reference: `backend/app/services/search_benchmark.py`, `backend/app/api/benchmarks.py`, `backend/app/api/search.py`.

### Qualitative results

The system performs well on concrete, descriptive queries. Example searches that return highly relevant results:

- `"airplane"` → frames of aircraft in flight, on runways, in hangars
- `"road"` → frames with roads during motion and when still
- `"person"` → action frames of people

### Known failure modes

A structured error analysis is in [docs/ERROR_ANALYSIS.md](docs/ERROR_ANALYSIS.md). Key categories:

1. **Abstract concepts** (e.g. `"love"`) — CLIP embeddings favor literal visuals, not emotional labels.
2. **Spatial / relational queries** (e.g. `"cat on top of table"`) — global image embeddings do not preserve fine layout.
3. **Negation** (e.g. `"person without hat"`) — contrastive training does not model logical negation.
4. **Fine-grained distinctions** (e.g. golden vs labrador retriever) — caption noise and visual similarity.
5. **OCR / text in images** — the vision encoder treats text as texture, not as transcribed characters.

See [`ERROR_ANALYSIS.md`](ERROR_ANALYSIS.md) for screenshot, detailed analysis, and proposed mitigations.

### Reproducing numbers (optional scripts)

With a built index under `backend/database/`, from the repo root:

```bash
cd backend
python ../scripts/benchmark_search.py
python ../scripts/benchmark_index.py
```

`benchmark_search.py` reports `ntotal`, mean / p50 / p95 end-to-end search latency and approximate QPS. `benchmark_index.py` reports indexing wall time and embeddings/sec. Record GPU and driver (`nvidia-smi`) with your numbers.

**Demo retrieval benchmark.** After indexing the optional demo corpus (`python scripts/fetch_demo_dataset.py` then point `POST /index` at `data/demo_corpus`), use **Benchmarks → Run demo retrieval test** or `POST /benchmarks/demo-retrieval`. Test cases: [`backend/benchmarks/demo_retrieval.json`](backend/benchmarks/demo_retrieval.json). Report top-k hit rate in your write-up if required.

**Course:** Duke CS 372 — Introduction to Applied Machine Learning, Spring 2026. See course policies for reuse.

## Individual Contributions

| Team member | NetID | Primary contributions |
|-------------|-------|-------------------------|
| Michael Setji | mps69 | **Backend core:** initial FastAPI layout, `environment.yml`, and service/module structure. **Indexing:** batched CLIP encoding, threaded image/video prefetch, progress reporting, cancel path, merge vs full-replace index logic (`indexer.py`, `index.py`, `index_state.py`). **GPU / performance:** FP16 autocast, optional FAISS-GPU search path, VRAM cleanup after indexing (`clip_service.py`, `faiss_store.py`). **Benchmarks API:** search latency + random / gibberish / random-unit baselines, demo retrieval spec (`benchmarks.py`, `search_benchmark.py`, `demo_retrieval_benchmark.py`). **Infra:** indexing lock, corrupt-index handling, SQLite + FAISS atomic saves, library/logs routes. |
| Kabir Gupta | kg331 | **Frontend UX:** About page, tab navigation (Search / Library / Benchmarks / Logs / About), demo screenshot and evaluation materials (`frontend/src/components/About.tsx`, `App.tsx`). **Documentation & submission (with partner):** README evaluation and qualitative sections, `docs/ERROR_ANALYSIS.md`, `SELF_ASSESSMENT.md`—split editing/review with Michael. **Reviews:** UI via PR `kabir-changes1`. **GPU / performance:** CUDA CLIP inference timing implementation. |
