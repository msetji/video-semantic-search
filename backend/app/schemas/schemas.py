from typing import Any, Literal

from pydantic import BaseModel, Field


class IndexRequest(BaseModel):
    root_path: str | None = Field(
        default=None,
        description="Absolute path to index, or Path relative to MEDIA_ROOT (e.g. 'vacation'). Empty = scan all of MEDIA_ROOT.",
    )
    root_paths: list[str] | None = Field(
        default=None,
        description=(
            "Optional list of absolute paths or MEDIA_ROOT-relative paths to index in one run. "
            "When provided, this takes precedence over root_path."
        ),
    )
    run_in_background: bool = Field(
        default=False,
        description="If true, return 202 immediately and run indexing in a background task (poll GET /index/status).",
    )
    replace_entire_index: bool = Field(
        default=False,
        description=(
            "If true, discard the existing index and replace it with only this run. "
            "If false (default), keep embeddings from other folders and only refresh paths under this scan root."
        ),
    )


class IndexResponse(BaseModel):
    root: str
    images_indexed: int
    videos_indexed: int
    embeddings: int  # total embeddings in the index after this run


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
    media_filter: Literal["both", "images", "videos"] = Field(
        default="both",
        description="Restrict hits to images, videos, or both (default).",
    )


class SearchHit(BaseModel):
    path: str
    kind: str
    time_sec: float | None
    score: float
    media_url: str


class SearchResponse(BaseModel):
    query: str
    results: list[SearchHit]


class BenchmarkSearchRequest(BaseModel):
    iterations: int = Field(default=40, ge=1, le=500)
    top_k: int = Field(default=10, ge=1, le=100)
    media_filter: Literal["both", "images", "videos"] = Field(default="both")
    seed: int = Field(default=42, description="RNG seed for random-corpus baseline sampling")


class BenchmarkSearchResponse(BaseModel):
    ntotal: int
    iterations: int
    top_k: int
    media_filter: str
    latency_mean_s: float
    latency_p50_s: float
    latency_p95_s: float
    qps: float
    semantic_mean_topk: float = Field(
        description="Mean cosine similarity of top-k hits for rotating natural-language queries.",
    )
    random_corpus_mean_topk: float = Field(
        description="Mean cosine of query vs k random embeddings from the index (unrelated content).",
    )
    gibberish_mean_topk: float = Field(
        description="Mean top-k similarity for nonsense text queries (CLIP still encodes a direction).",
    )
    random_query_unit_mean_topk: float = Field(
        description="Mean top-k similarity when the query vector is a random unit direction.",
    )
    semantic_over_random_corpus: float = Field(
        description="semantic_mean_topk / (random_corpus_mean_topk + eps); >1 means better than random corpus match.",
    )
    semantic_over_gibberish: float = Field(
        description="semantic_mean_topk / (gibberish_mean_topk + eps).",
    )


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


class DemoRetrievalRequest(BaseModel):
    top_k: int = Field(default=12, ge=1, le=100)
    media_filter: Literal["both", "images", "videos"] = Field(
        default="both",
        description="Use 'both' so video test cases are eligible (matches live search).",
    )


class DemoRetrievalCaseOut(BaseModel):
    label: str
    query: str
    path_includes: str
    expected_in_index: bool = Field(
        description="True if some indexed metadata path contains `path_includes` (case-insensitive).",
    )
    rank: int | None = Field(
        default=None,
        description="1-based position among a deep FAISS search; null if missing from index or past search cap.",
    )
    in_top_k: bool
    best_score: float | None = None
    latency_ms: float = Field(
        default=0.0,
        description="Encode + search time for this query only (ms).",
    )
    note: str | None = None


class DemoRetrievalResponse(BaseModel):
    ntotal: int
    top_k: int
    media_filter: str
    spec_version: int
    spec_description: str
    cases: list[DemoRetrievalCaseOut]
    pass_count: int
    case_count: int
    recall: float = Field(
        description="Fraction of cases where the expected file appears in the top-k list.",
    )
    search_rank_depth: int = Field(
        description="FAISS neighbor count used to compute rank (min(ntotal, cap)).",
    )
    count_expected_in_index: int
    count_not_in_index: int


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
