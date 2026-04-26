# CS 372 Final Project — Self-Assessment

**Course:** Duke CS 372 — Introduction to Applied Machine Learning, Spring 2026  
**Project:** Local Semantic Video & Photo Search (CLIP + FAISS, FastAPI + React)  
**Repository:** [fill Gradescope link]

**Team**

| Name          | NetID  |
|---------------|--------|
| Michael Setji | mps69  |
| Kabir Gupta   | kg331  |

**How to use this document:** For Gradescope, copy each claimed row into the official `self_assessment_template` from Canvas. The handout allows **at most 15 selections** in the **Machine Learning** category; only the first 15 count if you list more. Each distinct piece of work is claimed under **one** ML item below (plus Following Directions / Cohesion as applicable).

---

## Category 1 — Machine Learning (15 selections)

Below are **15** items we intend to claim, with **evidence** pointers for graders.

| # | Handout item (concise label) | Pts | Evidence |
|---|------------------------------|-----|----------|
| 1 | Modular code design (reusable functions/classes vs monolithic scripts) | 3 | Split layout: `backend/app/services/*.py`, `backend/app/api/*.py`, `frontend/src/components/*.tsx`; tests under `backend/tests/`, `frontend/src/utils/*.test.ts`. |
| 2 | Created baseline model for comparison (constant / random / simple heuristic) | 3 | `backend/app/services/search_benchmark.py`: semantic queries vs **random corpus embeddings**, **gibberish text** queries, **random unit** query vectors; ratios in `POST /benchmarks/search` (`backend/app/api/benchmarks.py`). |
| 3 | Properly normalized / standardized inputs appropriate to modality | 3 | CLIP L2-normalized embeddings: `backend/app/services/clip_service.py`; ImageNet normalization + resize/crop pipeline: `backend/app/services/indexer.py` (`fast_transform`); cosine = inner product: `DESIGN.md`, `backend/app/services/faiss_store.py`. |
| 4 | Basic preprocessing appropriate to modality (resize, handling bad inputs, etc.) | 3 | Images: `indexer.py` (`_to_model_input`, large-image downscale). Video: `backend/app/services/video_sampling.py` (~1 FPS, `max_frames_per_video` in `backend/app/config.py`). Skips corrupt media in indexer. |
| 5 | **Used** a vision–language model (CLIP, etc.) for multimodal tasks (text-to-image search, zero-shot, video understanding) | 5 | End-to-end text → image/video frame retrieval: `clip_service.py`, `backend/app/api/search.py`, `faiss_store.py`; default model id `backend/app/config.py` → `settings.clip_model_id`. |
| 6 | Deployed model as functional web application with user interface | 10 | `frontend/src/App.tsx` (Search, Library, Benchmarks, Logs, About), FastAPI app `backend/app/main.py`. |
| 7 | Measured and reported inference time, throughput, or computational efficiency | 3 | **README.md** → Evaluation (mean / p50 / p95 ms, QPS); reproduced via `POST /benchmarks/search` or Benchmarks UI; implementation `search_benchmark.py`, `benchmarks.py`. Per-request log line in `backend/app/api/search.py` (`Search complete … ms`). |
| 8 | Used at least three distinct and appropriate evaluation metrics for the task | 3 | Same benchmark response: e.g. **latency** (mean_s / p95_s), **throughput** (`qps`), **retrieval strength** (`semantic_mean_topk`, `semantic_over_random_corpus`, `semantic_over_gibberish`); see `backend/app/schemas/schemas.py` `BenchmarkSearchResponse`. Optional: `POST /benchmarks/demo-retrieval` → `recall` in `demo_retrieval_benchmark.py`. |
| 9 | Compared multiple model architectures or approaches quantitatively with controlled setup | 7 | **Not** different backbone nets; **controlled comparison** of **retrieval signal vs baselines** on the same index: semantic vs random-corpus vs gibberish vs random-query-unit (`search_benchmark.py` + README / benchmark JSON output). |
| 10 | Performed error analysis with visualization and discussion of failure cases | 7 | `ERROR_ANALYSIS.md` (abstract queries, why CLIP fails, mitigations); screenshot path referenced there. README → Known Failure Modes + link. |
| 11 | Conducted both qualitative and quantitative evaluation with thoughtful discussion | 5 | **Quantitative:** README Evaluation table (latency, QPS) + benchmark metrics above. **Qualitative:** README Qualitative Results + `ERROR_ANALYSIS.md`. |
| 12 | Analyzed model behavior on edge cases or out-of-distribution examples | 5 | Abstract / compositional queries in `ERROR_ANALYSIS.md`; API behavior for **corrupt / empty index** (`CorruptIndexError`, HTTP 503) in `faiss_store.py`, `search.py`, `benchmarks.py`; tests e.g. `backend/tests/test_index_state.py`, `test_media_allowlist.py`. |
| 13 | In technical walkthrough, explained architecture or mechanism of a pretrained model beyond surface level | 3 | **Evidence:** Technical walkthrough video (link in README when posted). Content should cover CLIP contrastive objective, text/image towers, and why inner product search matches normalized embeddings (align with `DESIGN.md` / `clip_service.py`). |
| 14 | Documented a design decision between ML approaches using technical tradeoffs with evidence | 3 | `DESIGN.md`: flat `IndexFlatIP` vs approximate indices; local-only constraint; GPU CLIP vs FAISS GPU notes; indexing concurrency. |
| 15 | In ATTRIBUTION.md, substantive account of AI tool use (generated vs modified vs debugged) | 3 | `ATTRIBUTION.md` (expand rows if additional tools used before submission). |

**Items we are *not* claiming (avoid overlap / wording mismatch)**

- **“Trained model using GPU/CUDA”** — we use GPU for **inference** and indexing encodes where available; we do **not** run a separate supervised **training** loop. Evidence for compute is under **inference timing** and **DESIGN.md** instead.
- **Fine-tuned / adapted CLIP (10-pt tier)** — no fine-tuning pipeline shipped.
- **Train/val/test split, training curves, DataLoader, optimizers** — not applicable to this retrieval-only PoC.

**Note for graders:** `ERROR_ANALYSIS.md` mentions `clip-vit-large-patch14` in prose; the **shipped default** in code is `openai/clip-vit-base-patch32` (`backend/app/config.py`). Align prose with config before final record, or note env override if you use one.

---

## Category 2 — Following Directions

Check each that applies after you finalize submission artifacts.

| Item | Status | Evidence |
|------|--------|----------|
| Self-assessment submitted with ≤15 ML selections + evidence | ☐ | This file + Gradescope |
| `SETUP.md` — step-by-step install | ☐ | `SETUP.md` |
| `ATTRIBUTION.md` — sources + AI disclosure | ☐ | `ATTRIBUTION.md` (update if more AI tools used) |
| `environment.yml` (or `requirements.txt`) accurate | ☐ | `environment.yml` |
| README — What it Does (one paragraph) | ☐ | `README.md` |
| README — Quick Start | ☐ | `README.md` |
| README — Video Links (direct links) | ☐ | **TODO:** replace placeholders in `README.md` |
| README — Evaluation (metrics / qualitative) | ☐ | `README.md` + `ERROR_ANALYSIS.md` |
| README — Individual Contributions (partners) | ☐ | **TODO:** fill “Primary contributions” column in `README.md` |
| Demo video — correct length & audience | ☐ | Link in README |
| Technical walkthrough — code + ML + contributions | ☐ | Link in README |
| Project workshop day 1–4 (if applicable) | ☐ | [fill attendance as required] |

---

## Category 3 — Project Cohesion and Motivation

| Item | Status | Evidence |
|------|--------|----------|
| README states unified goal / question | ☐ | `README.md` What it Does |
| Demo explains why project matters (non-technical) | ☐ | Demo video |
| Addresses real-world / meaningful problem | ☐ | Local privacy-preserving search; `DESIGN.md` motivation |
| Walkthrough shows components working together | ☐ | Technical walkthrough video |
| Clear progression problem → approach → solution → evaluation | ☐ | README + DESIGN + Evaluation |
| Design choices justified in docs or video | ☐ | `DESIGN.md`, README, walkthrough |
| Evaluation metrics match stated objectives | ☐ | Retrieval + latency in README / benchmarks |
| No “point collecting” unrelated to goal | ☐ | All claimed ML tied to retrieval pipeline |
| Clean codebase / no stale cruft | ☐ | Ongoing hygiene before tag |

---

## Quick evidence index (files)

| Topic | Files |
|-------|--------|
| Search API | `backend/app/api/search.py` |
| Benchmarks API | `backend/app/api/benchmarks.py` |
| Latency + baselines | `backend/app/services/search_benchmark.py` |
| Labeled demo retrieval | `backend/app/services/demo_retrieval_benchmark.py`, `backend/benchmarks/demo_retrieval.json` |
| CLIP | `backend/app/services/clip_service.py` |
| FAISS + GPU path + integrity | `backend/app/services/faiss_store.py` |
| Indexing / batching | `backend/app/services/indexer.py` |
| Indexing API / concurrency | `backend/app/api/index.py`, `index_state.py`, `indexing_lock.py` |
| UI | `frontend/src/App.tsx`, `frontend/src/components/*.tsx` |
| Indexing benchmark script | `scripts/benchmark_index.py` |

---

*Last generated to match repository layout and docs as of this commit; update Video Links, contributions column, workshop rows, and ATTRIBUTION before final submission.*
