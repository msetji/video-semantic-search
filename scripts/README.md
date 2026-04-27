# Utility scripts

Run these from the **repository root** with the `video-semantic-search` conda environment active unless noted otherwise. Full benchmark and setup details are in [SETUP.md](../SETUP.md). The app’s `POST /index` API (and the UI) also support `root_paths` to scan multiple folders in one run—see the Backend section there.

| Script | Purpose |
|--------|---------|
| [`fetch_demo_dataset.py`](fetch_demo_dataset.py) | Download optional image/video demo corpus into `data/demo_corpus/` (gitignored) plus manifest and suggested queries. |
| [`baseline_clip.py`](baseline_clip.py) | Quick CLIP text–image cosine check on one image file (defaults to `openai/clip-vit-base-patch32`). |
| [`sample_video_frames.py`](sample_video_frames.py) | Export ~1 FPS frames from an MP4 using the same sampling logic as the indexer. |
| [`benchmark_search.py`](benchmark_search.py) | Measure search latency (text encode + FAISS) on the current index; requires a built index under `backend/database/`. |
| [`benchmark_index.py`](benchmark_index.py) | Time a full index rebuild for `MEDIA_ROOT` or a `--root` subfolder. |

## `scripts/dev/` (optional, not required for the app)

| Script | Purpose |
|--------|---------|
| [`dev/probe_nvdec.py`](dev/probe_nvdec.py) | Probe PyAV / NVDEC availability. |
| [`dev/test_sampling.py`](dev/test_sampling.py) | Exercises video frame sampling. |
| [`dev/test_batch_timing.py`](dev/test_batch_timing.py) | Batch timing helper for encoding experiments. |

Each dev script documents its CLI in the module docstring.
