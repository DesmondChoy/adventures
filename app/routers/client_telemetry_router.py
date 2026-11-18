"""
Client Telemetry Router
Lets the browser log a small, fixed set of funnel events into telemetry_events.

Used for chapter-1 drop-off milestones that only the client can observe
(text shown, choices shown, choice clicked, page left before choosing).
"""

import logging
from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.auth.dependencies import get_current_user_id_optional
from app.rate_limit import limiter
from app.services.telemetry_service import TelemetryService

logger = logging.getLogger("client_telemetry_router")

router = APIRouter(prefix="/api/telemetry", tags=["telemetry"])

# Event name -> chapter number it describes. Anything else is rejected.
ALLOWED_CLIENT_EVENTS: Dict[str, int] = {
    "chapter1_text_shown": 1,
    "chapter1_choices_shown": 1,
    "chapter1_choice_clicked": 1,
    "chapter1_exit": 1,
}
ALLOWED_METADATA_KEYS = {"ms_since_start", "last_milestone", "trigger", "client_uuid"}
MAX_METADATA_STRING_LENGTH = 100


class ClientEvent(BaseModel):
    event_name: str
    adventure_id: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


def get_telemetry_service_dep() -> TelemetryService:
    return TelemetryService()


def sanitize_client_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Keep only known keys with short string or non-negative integer values."""
    clean: Dict[str, Any] = {}
    for key in ALLOWED_METADATA_KEYS:
        value = metadata.get(key)
        if isinstance(value, bool):
            continue
        if isinstance(value, (int, float)) and value >= 0:
            clean[key] = int(value)
        elif isinstance(value, str) and value.strip():
            clean[key] = value.strip()[:MAX_METADATA_STRING_LENGTH]
    return clean


@router.post("/client-event", status_code=204)
@limiter.limit("30/minute")
async def log_client_event(
    request: Request,
    event: ClientEvent,
    user_id: Optional[UUID] = Depends(get_current_user_id_optional),
    telemetry_service: TelemetryService = Depends(get_telemetry_service_dep),
):
    chapter_number = ALLOWED_CLIENT_EVENTS.get(event.event_name)
    if chapter_number is None:
        raise HTTPException(status_code=400, detail="Unknown event_name")

    try:
        adventure_uuid = UUID(event.adventure_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid adventure_id format")

    await telemetry_service.log_event(
        event_name=event.event_name,
        adventure_id=adventure_uuid,
        user_id=user_id,
        metadata=sanitize_client_metadata(event.metadata),
        chapter_number=chapter_number,
    )
