import uuid
from datetime import datetime, timedelta
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("story_app")


class StateStorageService:
    """
    Singleton service for storing and retrieving state data.
    All instances share the same memory cache.
    """

    _instance = None
    _memory_cache = {}  # Shared memory cache across all instances
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(StateStorageService, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not StateStorageService._initialized:
            StateStorageService._initialized = True
            logger.info("Initializing StateStorageService singleton")

    async def store_state(self, state_data: Dict[str, Any]) -> str:
        """Store state data and return a unique ID."""
        state_id = str(uuid.uuid4())
        StateStorageService._memory_cache[state_id] = {
            "state": state_data,
            "created_at": datetime.now(),
            "expires_at": datetime.now() + timedelta(hours=1),
        }
        logger.info(f"Stored state with ID: {state_id}")
        logger.info(
            f"Memory cache now contains {len(StateStorageService._memory_cache)} items"
        )
        logger.info(
            f"Memory cache keys: {list(StateStorageService._memory_cache.keys())}"
        )
        return state_id

    async def get_state(self, state_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve state data by ID."""
        logger.info(f"Attempting to retrieve state with ID: {state_id}")
        logger.info(
            f"Memory cache contains {len(StateStorageService._memory_cache)} items"
        )
        logger.info(
            f"Memory cache keys: {list(StateStorageService._memory_cache.keys())}"
        )

        state_data = StateStorageService._memory_cache.get(state_id)
        if not state_data:
            logger.warning(f"State not found: {state_id}")
            return None

        if state_data["expires_at"] < datetime.now():
            logger.warning(f"State expired: {state_id}")
            del StateStorageService._memory_cache[state_id]
            return None

        logger.info(f"Successfully retrieved state with ID: {state_id}")
        return state_data["state"]

    async def cleanup_expired(self) -> int:
        """Remove expired states and return count of removed items."""
        now = datetime.now()
        expired_keys = [
            k
            for k, v in StateStorageService._memory_cache.items()
            if v["expires_at"] < now
        ]
        for key in expired_keys:
            del StateStorageService._memory_cache[key]

        if expired_keys:
            logger.info(f"Cleaned up {len(expired_keys)} expired states")
        return len(expired_keys)
