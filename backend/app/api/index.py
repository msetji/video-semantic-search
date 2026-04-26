import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse

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


def _rebuild_index_and_mark_state_completed(root_path: str | None) -> dict:
    stats = rebuild_index(
        root_path,
        progress_callback=index_state.set_embedding_count,
        file_progress_callback=index_state.set_file_progress,
    )
    index_state.complete(stats)
    return stats


def run_scheduled_background_index_job(root_path: str | None) -> None:
    with INDEXING_LOCK:
        try:
            _rebuild_index_and_mark_state_completed(root_path)
        except Exception as e:  # noqa: BLE001
            logger.exception("Background indexing failed")
            index_state.fail(str(e))


@router.post("/index")
def run_index(body: IndexRequest, background_tasks: BackgroundTasks):
    if body.run_in_background:
        with INDEXING_LOCK:
            if index_state.is_running():
                raise HTTPException(
                    status_code=409,
                    detail="Indexing already in progress; use GET /index/status or wait.",
                )
            index_state.start()
        background_tasks.add_task(run_scheduled_background_index_job, body.root_path)
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
            stats = _rebuild_index_and_mark_state_completed(body.root_path)
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
