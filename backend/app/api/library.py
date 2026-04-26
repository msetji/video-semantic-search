from __future__ import annotations

from collections import defaultdict
from pathlib import PurePosixPath
from typing import Any

from fastapi import APIRouter, HTTPException

from app.schemas.schemas import (
    LibraryDirectory,
    LibraryFile,
    LibraryRemoveRequest,
    LibraryRemoveResponse,
    LibraryResponse,
)
from app.services.faiss_store import get_faiss_store
from app.services.indexing_lock import INDEXING_LOCK
from app.services import index_state

router = APIRouter(tags=["library"])


def _build_library(metadata: list[dict[str, Any]]) -> LibraryResponse:
    # De-duplicate by file path, keeping frame count and max timestamp.
    files_by_path: dict[str, dict[str, Any]] = {}
    for row in metadata:
        path = row["path"]
        if path not in files_by_path:
            files_by_path[path] = {"kind": row["kind"], "frame_count": 0, "max_time_sec": None}
        files_by_path[path]["frame_count"] += 1
        ts = row["time_sec"]
        if ts is not None:
            prev = files_by_path[path]["max_time_sec"]
            if prev is None or ts > prev:
                files_by_path[path]["max_time_sec"] = ts

    # Group files by parent directory.
    dirs: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for file_path, info in files_by_path.items():
        parent = str(PurePosixPath(file_path).parent)
        dirs[parent].append({"path": file_path, **info})

    directories: list[LibraryDirectory] = []
    for dir_path, files in sorted(dirs.items()):
        dir_name = PurePosixPath(dir_path).name or dir_path
        file_entries = [
            LibraryFile(
                name=PurePosixPath(f["path"]).name,
                path=f["path"],
                kind=f["kind"],
                frame_count=f["frame_count"],
                duration_sec=f["max_time_sec"],
            )
            for f in sorted(files, key=lambda x: x["path"])
        ]
        directories.append(
            LibraryDirectory(
                name=dir_name,
                path=dir_path,
                file_count=len(file_entries),
                embedding_count=sum(f.frame_count for f in file_entries),
                files=file_entries,
            )
        )

    return LibraryResponse(
        total_files=sum(d.file_count for d in directories),
        total_embeddings=len(metadata),
        directories=directories,
    )


@router.get("/library", response_model=LibraryResponse)
def get_library() -> LibraryResponse:
    store = get_faiss_store()
    if store.is_corrupt:
        raise HTTPException(status_code=503, detail="Index is corrupt; re-run indexing.")
    return _build_library(store.metadata)


@router.post("/library/remove", response_model=LibraryRemoveResponse)
def remove_library_entries(body: LibraryRemoveRequest) -> LibraryRemoveResponse:
    if index_state.is_running():
        raise HTTPException(status_code=409, detail="Indexing is in progress; try again after it finishes.")

    store = get_faiss_store()
    if store.is_corrupt:
        raise HTTPException(status_code=503, detail="Index is corrupt; re-run indexing.")

    with INDEXING_LOCK:
        removed = store.remove_paths(set(body.paths), set(body.directories))
        if removed > 0:
            store.save()

    return LibraryRemoveResponse(
        removed_embeddings=removed,
        remaining_embeddings=len(store.metadata),
    )
