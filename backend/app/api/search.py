import logging
import time

from fastapi import APIRouter, HTTPException

from app.schemas.schemas import SearchHit, SearchRequest, SearchResponse
from app.config import settings
from app.exceptions import CorruptIndexError
from app.services.clip_service import get_clip_service
from app.services.faiss_store import get_faiss_store
from app.services.media_paths import encoded_static_url_path_for_media_relative_path

logger = logging.getLogger(__name__)

router = APIRouter(tags=["search"])


@router.post("/search", response_model=SearchResponse)
def search(body: SearchRequest) -> SearchResponse:
    logger.info("Search request: query=%r top_k=%d", body.query, body.top_k)
    t0 = time.perf_counter()
    try:
        clip = get_clip_service()
        store = get_faiss_store()
        t0 = time.perf_counter()
        qvec = clip.encode_text([body.query])[0]
        t1 = time.perf_counter()
        raw = store.search(qvec, body.top_k)
        t2 = time.perf_counter()
        clip_encode_sec = t1 - t0
        faiss_search_sec = t2 - t1
        total_sec = clip_encode_sec + faiss_search_sec
        logger.info(
            "search_timing clip_encode_sec=%.6f faiss_search_sec=%.6f total_sec=%.6f top_k=%d query_preview=%r",
            clip_encode_sec,
            faiss_search_sec,
            total_sec,
            body.top_k,
            (body.query[:120] + "…") if len(body.query) > 120 else body.query,
        )
    except CorruptIndexError as e:
        logger.error("Search aborted — corrupt index: %s", e)
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:  # noqa: BLE001
        logger.exception("Search failed for query=%r", body.query)
        raise HTTPException(status_code=500, detail=str(e)) from e

    hits: list[SearchHit] = []
    for meta, score in raw:
        rel = meta["path"]
        hits.append(
            SearchHit(
                path=rel,
                kind=meta.get("kind", "unknown"),
                time_sec=meta.get("time_sec"),
                score=score,
                media_url=encoded_static_url_path_for_media_relative_path(rel),
            )
        )
    return SearchResponse(
        query=body.query,
        results=hits,
        clip_encode_sec=clip_encode_sec,
        faiss_search_sec=faiss_search_sec,
        total_sec=total_sec,
    )


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "media_root": str(settings.media_root.resolve())}
