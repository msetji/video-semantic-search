# Attributions and AI tool usage (CS 372)

## Third-party software

- **PyTorch**, **transformers** (Hugging Face), **FAISS**, **FastAPI**, **Pydantic**, **SQLite**, **React**, **Vite**, and other libraries listed in [`environment.yml`](environment.yml) / [`frontend/package.json`](frontend/package.json).
- **CLIP** weights from Hugging Face (`openai/clip-vit-*`); default model id is configurable via `CLIP_MODEL_ID` in `backend/.env` (see [`backend/.env.example`](backend/.env.example)).

## Generative AI assistance

This project used **Cursor**, **Claude Code**, and **Google Antigravity** extensively. These tools contributed to a significant amount of frontend implementation, API planning, model-research support, base repository/folder structure setup, debugging, substantial documentation drafting, refactoring, and converting long scripts into a cleaner repository layout. The authors retained responsibility for architecture, correctness, and evaluation design.

| Area | What the tools helped with | What was reviewed or changed manually |
|------|---------------------------|--------------------------------------|
| **Frontend** | Large portions of component structure, hooks, TypeScript types, styling iterations, and UI refactors. | Final API contract alignment, media URL/CORS behavior, and UX flow for indexing and search. |
| **Backend & API design** | Initial repository/service structure, endpoint planning, route/scaffold drafting, typing patterns, and refactor suggestions from long scripts to modular files. | Final indexing semantics, FAISS/SQLite alignment, concurrency locking, path allowlisting, and benchmark endpoint behavior. |
| **ML research / model choices** | Background research support on CLIP-family options, retrieval tradeoffs, and evaluation framing. | Final model choice, benchmark interpretation, and claims used in write-up and walkthrough. |
| **Docs** | Substantial drafting/editing of README, SETUP, error-analysis/self-assessment phrasing, and checklist formatting. | Final technical accuracy checks for Windows paths, conda usage, API behavior, and reproducible benchmark commands. |

**Debugging and rework:** Several suggestions were rejected or rewritten after running tests (`pytest`, Vitest), validating against real media paths and GPU behavior, and reconciling docs with the running API and actual repository contents.

Log additional sessions below if needed.

| Date       | Tool | What you used it for | What you reviewed/changed manually |
|------------|------|----------------------|-------------------------------------|
| 2026-04-23 | Google Antigravity | Refactored frontend to a standard React file tree, improved backend naming/readability, and aligned README with project handout requirements. | Reviewed architectural changes to ensure behavior stayed correct. |
| 2026-04-24 to 2026-04-26 | Cursor + Claude Code | Built/iterated significant frontend pieces, planned API shape, explored model/evaluation options, reorganized repository structure, refactored long scripts, assisted debugging, and drafted large portions of project documentation. | Verified API/runtime behavior locally, revised technical claims, and edited outputs for final submission accuracy. |

**Policy:** Follow the course and department rules for disclosure. Keep this file accurate for grading.
