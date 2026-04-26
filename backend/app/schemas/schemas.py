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
    clip_encode_sec: float = Field(
        ...,
        description="Wall time for CLIP text encoding (single query vector).",
    )
    faiss_search_sec: float = Field(
        ...,
        description="Wall time for FAISS inner-product search over the index.",
    )
    total_sec: float = Field(
        ...,
        description="clip_encode_sec + faiss_search_sec (server-side search only).",
    )


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
    )
