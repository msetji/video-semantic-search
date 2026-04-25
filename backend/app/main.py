from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import index as index_routes
from app.api import search as search_routes
from app.config import settings


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
app.include_router(search_routes.router)

@app.get("/media")
def serve_media(path: str):
    from pathlib import Path
    from fastapi.responses import FileResponse
    from fastapi import HTTPException
    
    p = Path(path).resolve()
    if p.is_file():
        return FileResponse(p)
    raise HTTPException(status_code=404, detail="Media file not found. Have you moved it?")

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

