import logging
import os

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse

from app.exceptions import IndexCancelledError
from app.schemas.schemas import (
    IndexAccepted,
    IndexRequest,
    IndexResponse,
    IndexStatusResponse,
    snapshot_to_status,
)
from app.services.indexer import rebuild_index
from app.services.indexing_lock import INDEXING_LOCK
from app.services import index_state

logger = logging.getLogger(__name__)

router = APIRouter(tags=["index"])


def _normalize_scan_roots(body: IndexRequest) -> list[str | None]:
    raw_paths: list[str] = []
    if body.root_paths is not None:
        raw_paths.extend(body.root_paths)
    elif body.root_path is not None:
        raw_paths.append(body.root_path)

    cleaned = [p.strip() for p in raw_paths if isinstance(p, str) and p.strip()]
    if not cleaned:
        return [None]

    deduped: list[str] = []
    seen: set[str] = set()
    for path in cleaned:
        key = os.path.normcase(os.path.normpath(path))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(path)
    return deduped


def _rebuild_index_and_mark_state_completed(
    scan_roots: list[str | None],
    replace_entire_index: bool,
) -> dict:
    images_indexed = 0
    videos_indexed = 0
    total_embeddings = 0
    final_root = ""

    for i, root_path in enumerate(scan_roots):
        stats = rebuild_index(
            root_path,
            progress_callback=index_state.set_embedding_count,
            file_progress_callback=index_state.set_file_progress,
            replace_entire_index=replace_entire_index if i == 0 else False,
        )
        images_indexed += int(stats["images_indexed"])
        videos_indexed += int(stats["videos_indexed"])
        total_embeddings = int(stats["embeddings"])
        final_root = str(stats["root"])

    if len(scan_roots) > 1:
        roots = [r for r in scan_roots if r]
        final_root = f"{len(roots)} directories" if roots else final_root

    combined = {
        "root": final_root,
        "images_indexed": images_indexed,
        "videos_indexed": videos_indexed,
        "embeddings": total_embeddings,
    }
    index_state.complete(combined)
    return combined


def run_scheduled_background_index_job(
    scan_roots: list[str | None],
    replace_entire_index: bool,
) -> None:
    with INDEXING_LOCK:
        try:
            _rebuild_index_and_mark_state_completed(scan_roots, replace_entire_index)
        except IndexCancelledError:
            logger.info("Background indexing was cancelled by user.")
            index_state.mark_cancelled()
        except Exception as e:  # noqa: BLE001
            logger.exception("Background indexing failed")
            index_state.fail(str(e))


@router.post("/index")
def run_index(body: IndexRequest, background_tasks: BackgroundTasks):
    scan_roots = _normalize_scan_roots(body)
    if body.run_in_background:
        with INDEXING_LOCK:
            if index_state.is_running():
                raise HTTPException(
                    status_code=409,
                    detail="Indexing already in progress; use GET /index/status or wait.",
                )
            index_state.start()
        background_tasks.add_task(
            run_scheduled_background_index_job,
            scan_roots,
            body.replace_entire_index,
        )
        return JSONResponse(
            status_code=202,
            content=IndexAccepted().model_dump(),
        )
    with INDEXING_LOCK:
        if index_state.is_running():
            raise HTTPException(
                status_code=503,
                detail="Indexing already in progress (e.g. background job). Use GET /index/status or retry later.",
            )
        index_state.start()
        try:
            stats = _rebuild_index_and_mark_state_completed(
                scan_roots,
                body.replace_entire_index,
            )
            return IndexResponse(**stats)
        except ValueError as e:
            index_state.fail(str(e))
            raise HTTPException(status_code=400, detail=str(e)) from e
        except Exception as e:  # noqa: BLE001
            logger.exception("Indexing failed")
            index_state.fail(str(e))
            raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/index/status", response_model=IndexStatusResponse)
def index_status() -> IndexStatusResponse:
    return snapshot_to_status(index_state.snapshot())


@router.post("/index/cancel")
def cancel_index():
    if not index_state.request_cancel():
        raise HTTPException(status_code=409, detail="No indexing job is currently running.")
    logger.info("Cancellation requested by user.")
    return {"status": "cancel_requested"}
