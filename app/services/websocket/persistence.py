import asyncio
import logging
from typing import Any
from uuid import uuid4

from fastapi import WebSocket

from app.services.state_storage_service import StateStorageService

logger = logging.getLogger("story_app")

STATE_SAVE_MAX_ATTEMPTS = 3
STATE_SAVE_RETRY_BASE_DELAY_SECONDS = 0.25
STATE_SAVE_FAILED_MESSAGE = (
    "We couldn't sync your latest progress. Keep this tab open and try again "
    "in a moment."
)


async def store_state_with_retry(
    state_storage_service: StateStorageService,
    websocket: WebSocket,
    state_data: dict[str, Any],
    *,
    operation: str,
    notify_client: bool = True,
    max_attempts: int | None = None,
    retry_delay_seconds: float = STATE_SAVE_RETRY_BASE_DELAY_SECONDS,
    **store_kwargs: Any,
) -> str | None:
    """Persist state with bounded retries and report terminal failures.

    New adventures receive a preallocated ID so creation retries upsert the same
    record instead of creating duplicates.
    """
    adventure_id = store_kwargs.get("adventure_id")
    if not adventure_id:
        store_kwargs["new_adventure_id"] = str(uuid4())

    attempts = max_attempts or STATE_SAVE_MAX_ATTEMPTS

    for attempt in range(1, attempts + 1):
        try:
            return await state_storage_service.store_state(
                state_data,
                **store_kwargs,
            )
        except Exception as error:  # noqa: BLE001 - storage clients raise varied exceptions
            is_final_attempt = attempt == attempts
            log_method = logger.error if is_final_attempt else logger.warning
            log_method(
                "State persistence attempt failed",
                extra={
                    "adventure_id": adventure_id,
                    "attempt": attempt,
                    "max_attempts": attempts,
                    "operation": operation,
                    "error": str(error),
                },
                exc_info=is_final_attempt,
            )

            if not is_final_attempt:
                await asyncio.sleep(
                    retry_delay_seconds * (2 ** (attempt - 1))
                )

    if notify_client:
        try:
            await websocket.send_json(
                {
                    "type": "save_failed",
                    "message": STATE_SAVE_FAILED_MESSAGE,
                    "retryable": True,
                }
            )
        except Exception as notification_error:  # noqa: BLE001 - socket may already be closed
            logger.debug(
                "Could not notify client about state persistence failure",
                extra={
                    "adventure_id": adventure_id,
                    "operation": operation,
                    "error": str(notification_error),
                },
            )

    return None
