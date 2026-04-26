from typing import Any, Literal

from pydantic import BaseModel, Field


class IndexRequest(BaseModel):
    root_path: str | None = Field(
        default=None,
        description="Absolute path to index, or Path relative to MEDIA_ROOT (e.g. 'vacation'). Empty = scan all of MEDIA_ROOT.",
    )
    run_in_background: bool = Field(
        default=False,
        description="If true, return 202 immediately and run indexing in a background task (poll GET /index/status).",
    )


class IndexResponse(BaseModel):
    root: str
    images_indexed: int
    videos_indexed: int
    embeddings: int


class IndexAccepted(BaseModel):
    status: Literal["accepted"] = "accepted"
    message: str = "Indexing started; poll GET /index/status"


class IndexStatusResponse(BaseModel):
    status: str
    detail: str | None = None
    error: str | None = None
    embeddings_written: int = 0
    last_result: IndexResponse | None = None
    started_at: float | None = None
    finished_at: float | None = None
    current_file: str | None = None
    total_files: int = 0
    files_done: int = 0


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int = Field(default=10, ge=1, le=100)


class SearchHit(BaseModel):
    path: str
    kind: str
    time_sec: float | None
    score: float
    media_url: str


class SearchResponse(BaseModel):
    query: str
    results: list[SearchHit]


class LibraryFile(BaseModel):
    name: str
    path: str
    kind: str
    frame_count: int
    duration_sec: float | None


class LibraryDirectory(BaseModel):
    name: str
    path: str
    file_count: int
    embedding_count: int
    files: list[LibraryFile]


class LibraryResponse(BaseModel):
    total_files: int
    total_embeddings: int
    directories: list[LibraryDirectory]


class LibraryRemoveRequest(BaseModel):
    paths: list[str] = Field(default_factory=list, description="Exact file paths to remove")
    directories: list[str] = Field(default_factory=list, description="Directory paths; removes all files under them")


class LibraryRemoveResponse(BaseModel):
    removed_embeddings: int
    remaining_embeddings: int


def snapshot_to_status(data: dict[str, Any]) -> IndexStatusResponse:
    lr = data.get("last_result")
    last: IndexResponse | None = None
    if isinstance(lr, dict):
        last = IndexResponse(
            root=str(lr["root"]),
            images_indexed=int(lr["images_indexed"]),
            videos_indexed=int(lr["videos_indexed"]),
            embeddings=int(lr["embeddings"]),
        )
    return IndexStatusResponse(
        status=str(data["status"]),
        detail=data.get("detail"),
        error=data.get("error"),
        embeddings_written=int(data.get("embeddings_written") or 0),
        last_result=last,
        started_at=data.get("started_at"),
        finished_at=data.get("finished_at"),
        current_file=data.get("current_file"),
        total_files=int(data.get("total_files") or 0),
        files_done=int(data.get("files_done") or 0),
    )
