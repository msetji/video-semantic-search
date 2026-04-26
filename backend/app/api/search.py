import logging
import time
from typing import Any

from fastapi import APIRouter, HTTPException

from app.schemas.schemas import SearchHit, SearchRequest, SearchResponse
from app.config import settings
from app.exceptions import CorruptIndexError
from app.services.clip_service import get_clip_service
from app.services.faiss_store import get_faiss_store
from app.services.media_paths import encoded_static_url_path_for_media_relative_path

logger = logging.getLogger(__name__)


def _search_with_media_filter(
    store,
    qvec,
    top_k: int,
    media_filter: str,
) -> list[tuple[dict[str, Any], float]]:
    n = len(store.metadata)
    if n == 0:
        return []
    if media_filter == "both":
        return store.search(qvec, min(top_k, n))
    want_kind = "image" if media_filter == "images" else "video"
    k = min(n, max(top_k * 50, 200))
    while True:
        raw = store.search(qvec, k)
        filtered = [(m, s) for m, s in raw if m.get("kind") == want_kind]
        if len(filtered) >= top_k or k >= n:
            return filtered[:top_k]
        next_k = min(n, max(k * 2, k + top_k * 25))
        if next_k <= k:
            return filtered[:top_k]
        k = next_k

router = APIRouter(tags=["search"])


@router.post("/search", response_model=SearchResponse)
def search(body: SearchRequest) -> SearchResponse:
    logger.info(
        "Search request: query=%r top_k=%d media_filter=%s",
        body.query,
        body.top_k,
        body.media_filter,
    )
    t0 = time.perf_counter()
    try:
        clip = get_clip_service()
        store = get_faiss_store()
        qvec = clip.encode_text([body.query])[0]
        raw = _search_with_media_filter(store, qvec, body.top_k, body.media_filter)
    except CorruptIndexError as e:
        logger.error("Search aborted — corrupt index: %s", e)
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:  # noqa: BLE001
        logger.exception("Search failed for query=%r", body.query)
        raise HTTPException(status_code=500, detail=str(e)) from e

    hits: list[SearchHit] = []
    for meta, score in raw:
        rel = meta["path"]
        kind = meta.get("kind", "unknown")
        hits.append(
            SearchHit(
                path=rel,
                kind=kind,
                time_sec=meta.get("time_sec"),
                score=score,
                media_url=encoded_static_url_path_for_media_relative_path(rel),
            )
        )

    elapsed_ms = (time.perf_counter() - t0) * 1000
    logger.info(
        "Search complete: query=%r → %d results in %.1f ms (top score=%.3f)",
        body.query,
        len(hits),
        elapsed_ms,
        hits[0].score if hits else 0.0,
    )
    return SearchResponse(query=body.query, results=hits)


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "media_root": str(settings.media_root.resolve())}
