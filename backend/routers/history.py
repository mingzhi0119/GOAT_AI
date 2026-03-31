"""History router — exposes sidebar conversation session APIs."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response

from backend.config import get_settings
from backend.services import log_service
from goat_ai.config import Settings

router = APIRouter()


@router.get("/history")
def list_history(settings: Settings = Depends(get_settings)) -> dict[str, list[dict[str, object]]]:
    """Return session metadata rows for the history sidebar."""
    sessions = log_service.list_sessions(db_path=settings.log_db_path)
    return {"sessions": sessions}


@router.delete("/history", status_code=204)
def delete_all_history(settings: Settings = Depends(get_settings)) -> Response:
    """Delete all persisted sessions and related conversation rows."""
    log_service.delete_all_sessions(db_path=settings.log_db_path)
    return Response(status_code=204)


@router.get("/history/{session_id}")
def get_history_session(
    session_id: str,
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    """Return one full persisted session including all messages."""
    session = log_service.get_session(db_path=settings.log_db_path, session_id=session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.delete("/history/{session_id}", status_code=204)
def delete_history_session(
    session_id: str,
    settings: Settings = Depends(get_settings),
) -> Response:
    """Delete one persisted session."""
    log_service.delete_session(db_path=settings.log_db_path, session_id=session_id)
    return Response(status_code=204)
