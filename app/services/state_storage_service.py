import uuid
from datetime import datetime, timedelta
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("story_app")


class StateStorageService:
    def __init__(self):
        self.memory_cache = {}  # Simple in-memory cache

    async def store_state(self, state_data: Dict[str, Any]) -> str:
        """Store state data and return a unique ID."""
        state_id = str(uuid.uuid4())
        self.memory_cache[state_id] = {
            "state": state_data,
            "created_at": datetime.now(),
            "expires_at": datetime.now() + timedelta(hours=1),
        }
        logger.info(f"Stored state with ID: {state_id}")
        return state_id

    async def get_state(self, state_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve state data by ID."""
        state_data = self.memory_cache.get(state_id)
        if not state_data:
            logger.warning(f"State not found: {state_id}")
            return None

        if state_data["expires_at"] < datetime.now():
            logger.warning(f"State expired: {state_id}")
            del self.memory_cache[state_id]
            return None

        logger.info(f"Retrieved state with ID: {state_id}")
        return state_data["state"]

    async def cleanup_expired(self) -> int:
        """Remove expired states and return count of removed items."""
        now = datetime.now()
        expired_keys = [
            k for k, v in self.memory_cache.items() if v["expires_at"] < now
        ]
        for key in expired_keys:
            del self.memory_cache[key]

        if expired_keys:
            logger.info(f"Cleaned up {len(expired_keys)} expired states")
        return len(expired_keys)
