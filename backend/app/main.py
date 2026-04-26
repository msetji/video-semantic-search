import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.logging_config import setup_logging

setup_logging()


class _SuppressPolling(logging.Filter):
    _SUPPRESS = {"/index/status", "/api/logs"}

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        return not any(path in msg for path in self._SUPPRESS)


logging.getLogger("uvicorn.access").addFilter(_SuppressPolling())

from fastapi.middleware.cors import CORSMiddleware

from app.api import benchmarks as benchmarks_routes
from app.api import index as index_routes
from app.api import library as library_routes
from app.api import logs as logs_routes
from app.api import search as search_routes
from app.config import settings
from app.services.faiss_store import get_faiss_store


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.media_root.mkdir(parents=True, exist_ok=True)
    settings.faiss_index_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Pre-cache/Initialize model on the main thread to prevent CUDA deadlocking in Fastapi background worker threads
    from app.services.clip_service import get_clip_service
    get_clip_service()
    
    yield


app = FastAPI(title="Local Semantic Video & Photo Search", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(index_routes.router)
app.include_router(library_routes.router)
app.include_router(search_routes.router)
app.include_router(benchmarks_routes.router)
app.include_router(logs_routes.router)


@app.get("/media")
def serve_media(path: str):
    from pathlib import Path
    from fastapi.responses import FileResponse
    from fastapi import HTTPException

    media_root = settings.media_root.resolve()
    p_in = Path(path)
    if p_in.is_absolute():
        logical_norm = os.path.normpath(str(p_in))
    else:
        logical_norm = os.path.normpath(str(media_root / path))
    if not get_faiss_store().media_path_is_allowed(logical_norm, media_root):
        raise HTTPException(status_code=400, detail="Invalid path")
    candidate = Path(logical_norm) if p_in.is_absolute() else (media_root / path)
    resolved = candidate.resolve()
    if not resolved.is_file():
        raise HTTPException(status_code=404, detail="Media file not found. Have you moved it?")
    return FileResponse(resolved)

@app.get("/api/system/browse-directory")
def browse_directory():
    import tkinter as tk
    from tkinter import filedialog
    
    # Synchronous FastAPI endpoints run automatically in a separate threadpool!
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    folder_path = filedialog.askdirectory(parent=root, title="Select Directory to Index")
    root.destroy()
    
    return {"path": folder_path}

@app.get("/api/system/browse-directories")
def browse_directories():
    import tkinter as tk
    from tkinter import filedialog, messagebox

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    selected: list[str] = []
    while True:
        folder_path = filedialog.askdirectory(parent=root, title="Select Directory to Index")
        if not folder_path:
            break
        if folder_path not in selected:
            selected.append(folder_path)
        if not messagebox.askyesno(
            "Select Another Directory",
            "Add another directory to this indexing run?",
            parent=root,
        ):
            break

    root.destroy()
    return {"paths": selected}


@app.post("/api/system/reveal-file")
def reveal_file(body: dict):
    import subprocess
    from pathlib import Path
    from fastapi import HTTPException

    rel = body.get("path", "")
    if not isinstance(rel, str) or not rel.strip():
        raise HTTPException(status_code=400, detail="path is required")
    rel = rel.strip()

    media_root = settings.media_root.resolve()
    p_in = Path(rel)

    # Logical path under media_root — do not .resolve() before the boundary check,
    # or junctions/symlinks make the path "escape" media_root and fail validation.
    if p_in.is_absolute():
        logical_norm = os.path.normpath(str(p_in))
    else:
        logical_norm = os.path.normpath(str(media_root / rel))

    if not get_faiss_store().media_path_is_allowed(logical_norm, media_root):
        raise HTTPException(status_code=400, detail="Invalid path")

    abs_path = Path(logical_norm).resolve() if p_in.is_absolute() else (media_root / rel).resolve()
    if not abs_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    # /select highlights the file in Explorer without opening it
    subprocess.Popen(["explorer", "/select,", str(abs_path)])
    return {"revealed": str(abs_path)}

