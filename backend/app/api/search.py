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
        qvec = clip.encode_text([body.query])[0]
        raw = store.search(qvec, body.top_k)
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
