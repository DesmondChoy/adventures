import os
import logging
from typing import Optional, Dict, Any
from uuid import UUID

from supabase import create_client, Client as AsyncSupabaseClient  # Changed import
from supabase.lib.client_options import ClientOptions  # Changed import
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


class TelemetryService:
    """
    Service for logging telemetry events to Supabase.
    """

    def __init__(self):
        load_dotenv()
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_KEY")

        if not supabase_url or not supabase_key:
            logger.error(
                "Supabase URL or Service Key not found in environment variables."
            )
            raise ValueError("Supabase URL or Service Key not configured.")

        try:
            # Using supabase_py_async for consistency if other async operations are planned
            # If only sync operations are needed, supabase-py could also be used.
            # For now, assuming async client might be beneficial.
            options = ClientOptions(
                persist_session=False, auto_refresh_token=False
            )  # Adjust as needed
            self.supabase: AsyncSupabaseClient = create_client(  # Changed type hint
                supabase_url, supabase_key, options
            )
            logger.info("TelemetryService initialized with Supabase client.")
        except Exception as e:
            logger.error(
                f"Failed to initialize Supabase client in TelemetryService: {e}"
            )
            raise

    async def log_event(
        self,
        event_name: str,
        adventure_id: Optional[UUID] = None,
        user_id: Optional[
            UUID
        ] = None,  # Assuming user_id will be UUID if/when auth is implemented
        metadata: Optional[Dict[str, Any]] = None,
        app_environment: Optional[str] = None,
        chapter_type: Optional[str] = None,
        chapter_number: Optional[int] = None,
        event_duration_seconds: Optional[int] = None,
    ) -> None:
        """
        Logs an event to the telemetry_events table.

        Args:
            event_name: The name of the event (e.g., 'adventure_started').
            adventure_id: The UUID of the adventure, if applicable.
            user_id: The UUID of the user, if applicable.
            metadata: A dictionary of additional event-specific data.
            app_environment: The application environment (e.g., 'development', 'production').
        """
        if not event_name:
            logger.warning("Attempted to log event with no event_name.")
            return

        record = {
            "event_name": event_name,
            "adventure_id": str(adventure_id) if adventure_id else None,
            "user_id": str(user_id) if user_id else None,
            "metadata": metadata if metadata else {},
            "environment": app_environment
            if app_environment
            else os.getenv("APP_ENVIRONMENT", "unknown"),
            "chapter_type": chapter_type,
            "chapter_number": chapter_number,
            "event_duration_seconds": event_duration_seconds,
            # timestamp is handled by Supabase default now()
        }

        try:
            # Supabase-py-async uses execute() for inserts, updates, deletes
            # Removing await as .execute() for insert might not be an awaitable,
            # and the error "object APIResponse can't be used in 'await' expression" was observed.
            # Data is reportedly still being inserted successfully.
            response = self.supabase.table("telemetry_events").insert(record).execute()

            if response.data:
                logger.info(
                    f"Telemetry event '{event_name}' logged successfully. ID: {response.data[0].get('id')}"
                )
            else:
                # Handle cases where response.data might be empty or not as expected
                # For supabase-py-async, errors are typically raised as exceptions.
                # If no exception and no data, it might indicate an issue or an empty insert result.
                logger.warning(
                    f"Telemetry event '{event_name}' logged, but no data returned in response. Response: {response}"
                )

        except Exception as e:
            logger.error(f"Error logging telemetry event '{event_name}': {e}")
            # Depending on requirements, you might want to re-raise or handle differently


# Example usage (for testing purposes, would be removed or placed in a test file)
if __name__ == "__main__":
    import asyncio

    async def main():
        # This is a basic test, ensure .env is set up
        # In a real app, TelemetryService would be instantiated and used by other services.
        try:
            telemetry_service = TelemetryService()

            # Example event
            test_adventure_id = UUID(
                "a1b2c3d4-e5f6-7890-1234-567890abcdef"
            )  # Replace with a real or dummy UUID

            await telemetry_service.log_event(
                event_name="test_event_from_service",
                adventure_id=test_adventure_id,
                metadata={
                    "detail": "This is a test event from TelemetryService",
                    "value": 123,
                },
                app_environment="development_test",
                chapter_type="story",
                chapter_number=1,
                event_duration_seconds=15,
            )

            await telemetry_service.log_event(
                event_name="another_test_event",
                metadata={"info": "No adventure ID for this one"},
                chapter_type="lesson",
            )

            # Test with explicit None for adventure_id
            await telemetry_service.log_event(
                event_name="none_adventure_id_test",
                adventure_id=None,
                metadata={"status": "testing None adventure_id"},
                chapter_number=5,
                event_duration_seconds=1,
            )

        except Exception as e:
            logger.error(f"Error during TelemetryService test: {e}")

    async def get_adventure_total_duration(self, adventure_id: UUID) -> str:
        """
        Calculate total time spent on an adventure by summing choice_made event durations.
        
        Args:
            adventure_id: UUID of the completed adventure
            
        Returns:
            Formatted duration string (e.g., "15 mins", "1 min", "-- mins")
        """
        try:
            result = self.supabase.table("telemetry_events")\
                .select("event_duration_seconds")\
                .eq("adventure_id", str(adventure_id))\
                .eq("event_name", "choice_made")\
                .execute()
            
            if not result.data:
                logger.debug(f"No telemetry data found for adventure {adventure_id}")
                return "-- mins"
                
            # Sum all durations, treating None/null as 0
            total_seconds = sum(row.get("event_duration_seconds", 0) or 0 for row in result.data)
            
            if total_seconds == 0:
                logger.debug(f"Zero total duration calculated for adventure {adventure_id}")
                return "-- mins"
                
            # Convert to minutes, minimum 1 minute for any completed adventure
            mins = max(1, round(total_seconds / 60))
            return f"{mins} min{'s' if mins != 1 else ''}"
            
        except Exception as e:
            logger.warning(f"Failed to calculate adventure duration for {adventure_id}: {e}")
            return "-- mins"

    # asyncio.run(main()) # Comment out after testing
    pass


# Lazy instantiation to avoid environment variable loading issues during import
_telemetry_service = None


def get_telemetry_service():
    """Get or create the telemetry service instance."""
    global _telemetry_service
    if _telemetry_service is None:
        _telemetry_service = TelemetryService()
    return _telemetry_service
