import uuid
from datetime import datetime, timedelta
import logging
from typing import Dict, Any, Optional
import os
import json
from supabase import create_client, Client
from dotenv import load_dotenv

logger = logging.getLogger("story_app")


class StateStorageService:
    """
    Service for storing and retrieving adventure state data using Supabase.
    """

    def __init__(self):
        """Initialize the Supabase client."""
        load_dotenv()  # Load environment variables from .env file
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_KEY")

        if not supabase_url or not supabase_key:
            logger.error("Supabase URL or key not found in environment variables")
            raise ValueError("Supabase URL or key not found in environment variables")

        self.supabase: Client = create_client(supabase_url, supabase_key)
        logger.info("Initialized StateStorageService with Supabase client")

    async def store_state(
        self,
        state_data: Dict[str, Any],
        adventure_id: Optional[str] = None,
        user_id: Optional[str] = None,
        lesson_topic: Optional[str] = None,  # Add lesson_topic parameter
    ) -> str:
        """
        Store adventure state data in Supabase and return the unique ID.
        If adventure_id is provided, updates the existing record (upsert).
        If not provided, creates a new record.

        Args:
            state_data: The complete adventure state data
            adventure_id: Optional ID of an existing adventure to update
            user_id: Optional user ID for authenticated users

        Returns:
            str: The UUID of the stored adventure
        """
        try:
            # Extract key fields for dedicated columns
            story_category = None
            # Use passed lesson_topic if available, otherwise try extracting from metadata
            extracted_lesson_topic = lesson_topic
            if (
                not extracted_lesson_topic
                and "metadata" in state_data
                and "lesson_topic" in state_data["metadata"]
            ):
                extracted_lesson_topic = state_data["metadata"]["lesson_topic"]

            is_complete = False
            completed_chapter_count = 0
            client_uuid = None  # Keep this for extraction, but don't save to column

            # Extract story_category from metadata or selected_narrative_elements
            if "metadata" in state_data and "story_category" in state_data["metadata"]:
                story_category = state_data["metadata"]["story_category"]

            # Extract client_uuid from metadata if available (for anonymous users)
            if "metadata" in state_data and "client_uuid" in state_data["metadata"]:
                client_uuid = state_data["metadata"]["client_uuid"]

            # Determine if adventure is complete based on chapters
            chapters = state_data.get("chapters", [])
            completed_chapter_count = len(chapters)

            # Check if the last chapter is a CONCLUSION or SUMMARY chapter
            if completed_chapter_count > 0:
                last_chapter_type = chapters[-1].get("chapter_type", "").lower()
                is_complete = last_chapter_type in ["conclusion", "summary"]

            # Prepare the record for insertion/update
            record = {
                "user_id": user_id,
                "state_data": state_data,  # Supabase will handle JSON serialization
                "story_category": story_category,
                "lesson_topic": extracted_lesson_topic,  # Use the extracted/passed topic
                "is_complete": is_complete,
                "completed_chapter_count": completed_chapter_count,
                # Note: client_uuid is already stored within state_data.metadata.client_uuid
                # We don't need a separate column for it
                "environment": os.getenv(
                    "APP_ENVIRONMENT", "unknown"
                ),  # Add environment
            }

            if adventure_id:
                # Prepare record for UPDATE - only include fields that change during the adventure
                update_record = {
                    "state_data": state_data,
                    "is_complete": is_complete,
                    "completed_chapter_count": completed_chapter_count,
                    # updated_at is handled by the trigger
                }
                logger.info(f"Updating existing adventure with ID: {adventure_id}")
                response = (
                    self.supabase.table("adventures")
                    .update(update_record)  # Use the specific update record
                    .eq("id", adventure_id)
                    .execute()
                )

                if not response.data or len(response.data) == 0:
                    logger.error(
                        f"Failed to update adventure {adventure_id}: No data returned from Supabase"
                    )
                    raise ValueError(f"Failed to update adventure {adventure_id}")

                logger.info(f"Updated adventure with ID: {adventure_id}")
                logger.info(
                    f"Updated state with {completed_chapter_count} chapters and {len(state_data.get('chapter_summaries', []))} summaries"
                )
                return adventure_id
            else:
                # Insert new record
                response = self.supabase.table("adventures").insert(record).execute()

                # Extract the ID from the response
                if not response.data or len(response.data) == 0:
                    logger.error(
                        "Failed to store state: No data returned from Supabase"
                    )
                    raise ValueError(
                        "Failed to store state: No data returned from Supabase"
                    )

                adventure_id = response.data[0]["id"]
                logger.info(f"Stored new adventure with ID: {adventure_id}")
                logger.info(
                    f"Stored state with {completed_chapter_count} chapters and {len(state_data.get('chapter_summaries', []))} summaries"
                )

                return adventure_id

        except Exception as e:
            logger.error(f"Error storing state in Supabase: {str(e)}")
            raise

    async def get_state(self, state_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve adventure state data from Supabase by ID.

        Args:
            state_id: The UUID of the stored adventure

        Returns:
            Optional[Dict[str, Any]]: The adventure state data or None if not found
        """
        try:
            logger.info(f"Attempting to retrieve state with ID: {state_id}")

            # Query Supabase for the record
            response = (
                self.supabase.table("adventures")
                .select("state_data")
                .eq("id", state_id)
                .maybe_single()
                .execute()
            )

            # Check if data was found
            if not response.data:
                logger.warning(f"State not found: {state_id}")
                return None

            # Extract the state_data field
            retrieved_state = response.data["state_data"]

            logger.info(f"Successfully retrieved state with ID: {state_id}")
            logger.info(
                f"Retrieved state with {len(retrieved_state.get('chapters', []))} chapters and {len(retrieved_state.get('chapter_summaries', []))} summaries"
            )

            return retrieved_state

        except Exception as e:
            logger.error(f"Error retrieving state from Supabase: {str(e)}")
            return None

    async def get_active_adventure_id(self, client_uuid: str) -> Optional[str]:
        """
        Find an active (incomplete) adventure for the given client UUID.

        Args:
            client_uuid: The client's UUID stored in localStorage

        Returns:
            Optional[str]: The adventure ID if found, None otherwise
        """
        try:
            logger.info(f"Looking for active adventure for client UUID: {client_uuid}")

            # Query Supabase for incomplete adventures with matching client_uuid in the metadata
            # We need to use the JSON path syntax to query inside the JSONB field
            # Order by updated_at DESC to get the most recently updated one
            response = (
                self.supabase.table("adventures")
                .select("id, updated_at")
                .eq("state_data->'metadata'->>'client_uuid'", client_uuid)
                .eq("is_complete", False)
                .order("updated_at", desc=True)  # Corrected order syntax
                .limit(1)
                .execute()
            )

            # Check if any active adventure was found
            if response.data and len(response.data) > 0:
                adventure_id = response.data[0]["id"]
                logger.info(f"Found active adventure with ID: {adventure_id}")
                return adventure_id

            logger.info(f"No active adventure found for client UUID: {client_uuid}")
            return None

        except Exception as e:
            logger.error(f"Error finding active adventure: {str(e)}")
            return None

    async def cleanup_expired(self) -> int:
        """
        Remove adventures older than the expiration period (1 hour).

        Returns:
            int: Number of expired records deleted
        """
        try:
            # Calculate the expiration timestamp (1 hour ago)
            expiration_time = datetime.now() - timedelta(hours=1)

            # Delete expired records from Supabase
            response = (
                self.supabase.table("adventures")
                .delete()
                .lt("created_at", expiration_time.isoformat())
                .execute()
            )

            # Count the number of deleted records
            deleted_count = len(response.data) if response.data else 0

            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} expired states")

            return deleted_count

        except Exception as e:
            logger.error(f"Error cleaning up expired states: {str(e)}")
            return 0
