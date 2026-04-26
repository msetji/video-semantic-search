# Local setup (TAs & developers)

Engineering scope and limitations (flat FAISS search, full rebuilds, concurrency) are documented in [DESIGN.md](DESIGN.md).

## Prerequisites

- [Miniforge](https://github.com/conda-forge/miniforge) or Miniconda with `conda` / `mamba`
- NVIDIA GPU driver compatible with **CUDA 12.x** (project pins `pytorch-cuda=12.1`)
- Node.js **20+** and npm (for the frontend)

If `faiss-gpu` or CUDA PyTorch packages fail to solve on a machine without a suitable GPU/driver, install on a lab machine with an NVIDIA GPU or temporarily use CPU-only PyTorch and `faiss-cpu` for development (not for final demo).

## 1. Conda environment

If you are on Windows, open an **Anaconda Prompt** or **Miniconda Prompt** terminal (normal PowerShell or Command Prompt often will not recognize `conda` out-of-the-box). Then, from the repository root:

```bash
mamba env create -f environment.yml
# If you don't have mamba, you can use:
# conda env create -f environment.yml

conda activate video-semantic-search
```

## 2. Media directory

You **do not** need to move your photos (`.jpg`, `.jpeg`, `.png`, `.webp`) and videos (`.mp4`) to the `data/` directory!
The Video Semantic Search app has been upgraded to support absolute native directory mapping. When the frontend is running, you can simply click the **"Choose Directory"** button and pick any folder straight off your Windows hard drive. 

## 3. Backend (FastAPI)

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- **Health:** `GET http://127.0.0.1:8000/health`
- **Build / refresh index (blocking):** `POST http://127.0.0.1:8000/index` with JSON `{"root_path": "C:\\Path\\To\\Videos"}` to scan an absolute path on your disk, or leave `{"root_path": null}` to fallback to the internal `data/` folder.
- **Build index in background:** `POST` with `{"run_in_background": true}` → **202 Accepted**; poll **`GET http://127.0.0.1:8000/index/status`**. In-memory status **resets when the server restarts**. (Tip: You can start the background index directly from the frontend UI).
- **Search:** `POST http://127.0.0.1:8000/search` with `{"query": "your text", "top_k": 10}`. Returns **503** if the on-disk index is **corrupt** (metadata/FAISS mismatch); run `POST /index` again.

**Concurrency:** Only one indexing job may be **running** at a time. A second `POST /index` with `run_in_background: true` returns **409** while a background job is running. A synchronous `POST /index` returns **503** if a background indexer has reserved the job (`index_state` shows running).

Static files are dynamically streamed via the `GET /media?path={absolute_path}` endpoint pointing directly to the OS disk.

Optional environment (see `backend/app/config.py`): `MEDIA_ROOT`, **`MAX_FRAMES_PER_VIDEO`** (default **7200** ≈ 2 hours at 1 FPS sampled frames per MP4; longer clips are truncated).

### Index on-disk format (migration)

The index uses **`backend/database/faiss.index`** + **`backend/database/metadata.sqlite`** (row ids aligned with FAISS). If you have an older tree with **`metadata.json`** only, the server will **migrate** to SQLite when row counts match the FAISS file. Otherwise, delete `backend/database/*` (keep `.gitkeep`) and run `POST /index` again.

## 4. Frontend (Vite)

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

The dev server defaults to port **5173**. [`.env.development`](frontend/.env.development) sets `VITE_API_BASE=http://127.0.0.1:8000` so the UI talks to the API. For production builds, set `VITE_API_BASE` to the public API origin.

**Dev proxy:** `vite.config.ts` proxies `/media` to the backend so images and video previews can load without CORS issues when using relative `/media` URLs. The app uses absolute URLs from `VITE_API_BASE` for API calls; ensure the backend CORS list includes your dev origin if you change hosts/ports.

## 5. Baseline CLIP check

With the conda env active, from the repo root:

```bash
python scripts/baseline_clip.py path/to/image.jpg
```

This prints cosine similarity vs a fixed text string and rough wall time.

## 6. Video frame sampling (1 FPS)

```bash
python scripts/sample_video_frames.py path/to/video.mp4 ./out_frames
```

Adds `backend/` to `sys.path` and reuses `app.services.video_sampling`. Indexing uses the same ~1 FPS stride; see [DESIGN.md](DESIGN.md) for rationale and the **7200** frame cap.

Optional dev-only helpers (not part of the graded app) live under `scripts/dev/` — for example `probe_nvdec.py` (PyAV / NVDEC availability), `test_sampling.py`, and `test_batch_timing.py`. Run paths from the repo root; each file documents its CLI in the module docstring.

## 7. Benchmarks (reporting throughput and latency)

With the conda env active:

```bash
cd backend
python ../scripts/benchmark_search.py
python ../scripts/benchmark_index.py
python ../scripts/benchmark_index.py --root some_subfolder
```

Record in your write-up: **`ntotal`**, **GPU model**, **CUDA / driver** (`nvidia-smi`), **mean/p50/p95** search latency, and **embeddings/sec** during indexing. Compare CPU vs GPU FAISS at your scale if you toggle GPU availability (see [DESIGN.md](DESIGN.md)).

## 8. Performance notes (rubric)

For your write-up, tie numbers to **`nvidia-smi`** while indexing or searching; report batch sizes used in CLIP encoding (see `clip_service.py`).
