# Attributions and AI tool usage (CS 372)

## Third-party software

- **PyTorch**, **transformers** (Hugging Face), **FAISS**, **FastAPI**, **Pydantic**, **SQLite**, **React**, **Vite**, and other libraries listed in [`environment.yml`](environment.yml) / [`frontend/package.json`](frontend/package.json).
- **CLIP** weights from Hugging Face (`openai/clip-vit-*`); default model id is configurable via `CLIP_MODEL_ID` in `backend/.env` (see [`backend/.env.example`](backend/.env.example)).

## Generative AI assistance

This project used **Cursor** and similar assistants for acceleration (boilerplate, refactors, debugging, and documentation). The author retained responsibility for architecture, correctness, and evaluation design.

| Area | What the tools helped with | What was reviewed or changed manually |
|------|---------------------------|--------------------------------------|
| **Frontend** | Component structure, hooks, TypeScript types, styling iterations. | API contracts with the backend, media URL and CORS behavior, UX flow for indexing and search. |
| **Backend** | Service layout, FastAPI routes, typing, and test scaffolding suggestions. | Indexing semantics, FAISS/SQLite alignment, concurrency locking, path allowlisting, and benchmark endpoints. |
| **Docs** | README/SETUP phrasing and checklists. | Technical accuracy for Windows paths, conda usage, and reproducible benchmark commands. |

**Debugging and rework:** Several suggestions were rejected or rewritten after running tests (`pytest`, Vitest) or validating against real media paths and GPU behavior. When in doubt, behavior was verified against `DESIGN.md` and the running API.

Log additional sessions below if needed.

| Date       | Tool        | What you used it for | What you reviewed/changed manually |
|------------|-------------|----------------------|-------------------------------------|
| 2026-04-23 | Antigravity AI | Refactored frontend to standard React file tree, updated backend variable names for readability, and aligned README with the final project handout. | Reviewed the architectural changes to ensure functionality remained exact. |

**Policy:** Follow the course and department rules for disclosure. Keep this file accurate for grading.
