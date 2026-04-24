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

- [Insert benchmarking results, model latency, or throughput table here]
- See [DESIGN.md](DESIGN.md) for a discussion of scope, concurrency, and hardware tradeoffs.

## Individual Contributions

| Team member | NetID | Primary contributions |
|-------------|-------|-------------------------|
| Partner 1   | [ ]   |                       |
| Partner 2   | [ ]   |                       |

---
**Course:** Duke CS 372 — Introduction to Applied Machine Learning Spring 2026. See course policies for reuse.
