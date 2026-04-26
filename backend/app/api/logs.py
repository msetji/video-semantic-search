import logging

from fastapi import APIRouter

from app.logging_config import get_log_records

logger = logging.getLogger(__name__)
router = APIRouter(tags=["logs"])


@router.get("/api/logs")
def get_logs() -> dict:
    return {"logs": get_log_records()}
