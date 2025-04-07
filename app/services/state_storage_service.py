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
        self, state_data: Dict[str, Any], user_id: Optional[str] = None
    ) -> str:
        """
        Store adventure state data in Supabase and return the unique ID.

        Args:
            state_data: The complete adventure state data
            user_id: Optional user ID for authenticated users

        Returns:
            str: The UUID of the stored adventure
        """
        try:
            # Extract key fields for dedicated columns
            story_category = None
            lesson_topic = None
            is_complete = False
            completed_chapter_count = 0

            # Extract story_category from metadata or selected_narrative_elements
            if "metadata" in state_data and "story_category" in state_data["metadata"]:
                story_category = state_data["metadata"]["story_category"]

            # Extract lesson_topic from metadata or directly
            if "metadata" in state_data and "lesson_topic" in state_data["metadata"]:
                lesson_topic = state_data["metadata"]["lesson_topic"]

            # Determine if adventure is complete based on chapters
            chapters = state_data.get("chapters", [])
            completed_chapter_count = len(chapters)

            # Check if the last chapter is a CONCLUSION or SUMMARY chapter
            if completed_chapter_count > 0:
                last_chapter_type = chapters[-1].get("chapter_type", "").lower()
                is_complete = last_chapter_type in ["conclusion", "summary"]

            # Prepare the record for insertion
            record = {
                "user_id": user_id,
                "state_data": state_data,  # Supabase will handle JSON serialization
                "story_category": story_category,
                "lesson_topic": lesson_topic,
                "is_complete": is_complete,
                "completed_chapter_count": completed_chapter_count,
            }

            # Insert the record into Supabase
            response = self.supabase.table("adventures").insert(record).execute()

            # Extract the ID from the response
            if not response.data or len(response.data) == 0:
                logger.error("Failed to store state: No data returned from Supabase")
                raise ValueError(
                    "Failed to store state: No data returned from Supabase"
                )

            adventure_id = response.data[0]["id"]
            logger.info(f"Stored state with ID: {adventure_id}")
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
