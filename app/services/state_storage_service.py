import uuid  # Keep for adventure_id generation if needed, and for UUID type hint
from datetime import datetime, timedelta
import logging
from typing import Dict, Any, Optional
from uuid import UUID  # Import UUID for type hinting user_id
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
        user_id: Optional[UUID] = None,  # Changed type hint to Optional[UUID]
        lesson_topic: Optional[str] = None,
        explicit_is_complete: Optional[bool] = None,  # New parameter
    ) -> str:
        """
        Store adventure state data in Supabase and return the unique ID.
        If adventure_id is provided, updates the existing record (upsert).
        If not provided, creates a new record.

        Args:
            state_data: The complete adventure state data
            adventure_id: Optional ID of an existing adventure to update
            user_id: Optional user ID (as UUID object) for authenticated users

        Returns:
            str: The UUID of the stored adventure
        """
        try:
            user_id_for_db = str(user_id) if user_id is not None else None

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

            # Determine is_complete status
            if explicit_is_complete is not None:
                is_complete = explicit_is_complete
                logger.info(f"Using explicit_is_complete value: {is_complete}")
            elif completed_chapter_count > 0:
                last_chapter_type = chapters[-1].get("chapter_type", "").lower()
                is_complete = last_chapter_type in ["conclusion", "summary"]
                logger.info(
                    f"Derived is_complete based on last chapter type ({last_chapter_type}): {is_complete}"
                )
            else:
                is_complete = False  # Default for new/empty adventures
                logger.info(f"Defaulting is_complete to False for new/empty adventure.")

            # Prepare the record for insertion/update
            record = {
                "user_id": user_id_for_db,  # Use stringified user_id
                "state_data": state_data,  # Supabase will handle JSON serialization
                "story_category": story_category,
                "lesson_topic": extracted_lesson_topic,  # Use the extracted/passed topic
                "is_complete": is_complete,
                "completed_chapter_count": completed_chapter_count,
                "client_uuid": client_uuid,  # Add the extracted client_uuid here
                "environment": os.getenv(
                    "APP_ENVIRONMENT", "unknown"
                ),  # Add environment
            }

            if adventure_id:
                # Prepare record for UPDATE - include client_uuid as well
                update_record = {
                    "user_id": user_id_for_db,  # Add stringified user_id
                    "state_data": state_data,
                    "is_complete": is_complete,
                    "completed_chapter_count": completed_chapter_count,
                    "client_uuid": client_uuid,  # Add client_uuid to update_record
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
                # This is a new adventure. If a user_id is provided, abandon their old incomplete adventure.
                if user_id:
                    abandon_success = await self._abandon_existing_incomplete_adventure(
                        user_id
                    )
                    if not abandon_success:
                        # Log a warning but proceed with creating the new adventure.
                        # The alternative would be to raise an error and prevent new adventure creation,
                        # but that might be a worse UX if abandoning fails for some reason.
                        logger.warning(
                            f"Proceeding to create new adventure for user {user_id} despite failure to abandon previous one."
                        )

                # Insert new record
                # --- ADDED LOGGING ---
                logger.debug(
                    f"Attempting to insert new adventure record. State data being inserted (metadata check): {state_data.get('metadata', 'METADATA_KEY_MISSING')}"
                )
                # --- END ADDED LOGGING ---
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

    async def get_active_adventure_id(
        self,
        client_uuid: Optional[str] = None,
        user_id: Optional[UUID] = None,
        story_category: Optional[str] = None,
        lesson_topic: Optional[str] = None,
    ) -> Optional[str]:
        """
        Find an active (incomplete) adventure that matches the specified story and lesson.
        Prioritizes user_id if provided, otherwise uses client_uuid.

        Args:
            client_uuid: Optional client's UUID.
            user_id: Optional user's UUID from authentication.
            story_category: Optional story category to match.
            lesson_topic: Optional lesson topic to match.

        Returns:
            Optional[str]: The adventure ID if found, None otherwise.
        """
        if not user_id and not client_uuid:
            logger.warning(
                "get_active_adventure_id called without user_id or client_uuid."
            )
            return None

        try:
            # Build base query
            query = (
                self.supabase.table("adventures")
                .select("id, updated_at, story_category, lesson_topic")
                .eq("is_complete", False)
                .order("updated_at", desc=True)
                .limit(1)
            )

            # Add story/lesson filters if provided
            if story_category:
                query = query.eq("story_category", story_category)
            if lesson_topic:
                query = query.eq("lesson_topic", lesson_topic)

            adventure_id_found = None

            if user_id:
                logger.info(
                    f"Looking for active adventure for user_id: {user_id}"
                    f"{f', story: {story_category}' if story_category else ''}"
                    f"{f', lesson: {lesson_topic}' if lesson_topic else ''}"
                )
                response_user = query.eq("user_id", str(user_id)).execute()
                logger.debug(
                    f"Raw response from get_active_adventure_id query (user_id: {user_id}): {response_user}"
                )
                if response_user.data and len(response_user.data) > 0:
                    adventure_id_found = response_user.data[0]["id"]
                    logger.info(
                        f"Found matching active adventure with ID: {adventure_id_found} for user_id: {user_id}"
                    )
                    return adventure_id_found
                else:
                    logger.info(
                        f"No matching active adventure found for user_id: {user_id}"
                        f"{f' with story: {story_category}' if story_category else ''}"
                        f"{f' and lesson: {lesson_topic}' if lesson_topic else ''}"
                    )

            # If not found by user_id (or user_id was not provided) and client_uuid is available, try client_uuid
            if not adventure_id_found and client_uuid:
                logger.info(
                    f"Looking for active adventure for client_uuid: {client_uuid}"
                    f"{f', story: {story_category}' if story_category else ''}"
                    f"{f', lesson: {lesson_topic}' if lesson_topic else ''}"
                    f" (user_id search failed or user_id not provided)"
                )
                response_client = query.eq("client_uuid", client_uuid).execute()
                logger.debug(
                    f"Raw response from get_active_adventure_id query (client_uuid: {client_uuid}): {response_client}"
                )
                if response_client.data and len(response_client.data) > 0:
                    adventure_id_found = response_client.data[0]["id"]
                    logger.info(
                        f"Found matching active adventure with ID: {adventure_id_found} for client_uuid: {client_uuid}"
                    )
                    return adventure_id_found
                else:
                    logger.info(
                        f"No matching active adventure found for client_uuid: {client_uuid}"
                        f"{f' with story: {story_category}' if story_category else ''}"
                        f"{f' and lesson: {lesson_topic}' if lesson_topic else ''}"
                    )

            if not adventure_id_found:
                logger.info(
                    f"No active adventure found for user_id: {user_id} or client_uuid: {client_uuid}"
                )

            return None  # Explicitly return None if no adventure is found by either identifier

        except Exception as e:
            logger.error(
                f"Error finding active adventure (user_id: {user_id}, client_uuid: {client_uuid}): {str(e)}"
            )
            return None

    async def get_user_current_adventure(
        self, user_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """
        Get the user's single incomplete adventure with essential info for the resume modal.

        Args:
            user_id: The UUID of the user.

        Returns:
            Optional[Dict[str, Any]]: A dictionary containing adventure details if an
                                     incomplete adventure is found, otherwise None.
                                     The dictionary includes: adventure_id, story_category,
                                     lesson_topic, current_chapter (completed_chapter_count),
                                     total_chapters (from state_data.story_length),
                                     and last_updated (updated_at).
        """
        try:
            logger.info(f"Fetching current adventure for user_id: {user_id}")
            response = (
                self.supabase.table("adventures")
                .select(
                    "id, story_category, lesson_topic, completed_chapter_count, updated_at, state_data"
                )
                .eq("user_id", str(user_id))
                .eq("is_complete", False)
                .order("updated_at", desc=True)
                .limit(1)
                .maybe_single()
                .execute()
            )

            if not response.data:
                logger.info(
                    f"No active incomplete adventure found for user_id: {user_id}"
                )
                return None

            adventure_data = response.data
            story_length = adventure_data.get("state_data", {}).get("story_length")

            # Ensure current_chapter is at least 1 if chapters exist, or 0 if new
            current_chapter = adventure_data.get("completed_chapter_count", 0)
            if current_chapter > 0:
                # If chapters are completed, current_chapter for display is usually +1
                # However, for "Chapter X out of Y", completed_chapter_count is fine.
                # If modal shows "Chapter 3 of 10", it means 3 chapters are done.
                pass  # Using completed_chapter_count directly for "Chapter X"

            modal_info = {
                "adventure_id": adventure_data["id"],
                "story_category": adventure_data["story_category"],
                "lesson_topic": adventure_data["lesson_topic"],
                "current_chapter": current_chapter,
                "total_chapters": story_length,  # Can be None if not in state_data
                "last_updated": adventure_data["updated_at"],
            }
            logger.info(f"Found current adventure for user_id {user_id}: {modal_info}")
            return modal_info

        except Exception as e:
            logger.error(
                f"Error fetching current adventure for user_id {user_id}: {str(e)}"
            )
            return None

    async def abandon_adventure(self, adventure_id: str, user_id: UUID) -> bool:
        """
        Mark an adventure as abandoned (is_complete = True).
        Optionally, a 'completion_reason' could be set if the schema supports it.

        Args:
            adventure_id: The ID of the adventure to abandon.
            user_id: The UUID of the user who owns the adventure.

        Returns:
            bool: True if the adventure was successfully marked as abandoned, False otherwise.
        """
        try:
            logger.info(
                f"User {user_id} attempting to abandon adventure {adventure_id}"
            )
            # Consider adding a 'completion_reason' field to the table in a future migration
            # update_payload = {"is_complete": True, "completion_reason": "abandoned_by_user"}
            update_payload = {"is_complete": True}

            response = (
                self.supabase.table("adventures")
                .update(update_payload)
                .eq("id", adventure_id)
                .eq("user_id", str(user_id))  # Ensure user owns the adventure
                .eq("is_complete", False)  # Only abandon incomplete adventures
                .execute()
            )

            if response.data and len(response.data) > 0:
                logger.info(
                    f"Adventure {adventure_id} successfully abandoned by user {user_id}."
                )
                return True
            else:
                # This could happen if the adventure doesn't exist, user doesn't own it, or it's already complete.
                logger.warning(
                    f"Failed to abandon adventure {adventure_id} for user {user_id}. "
                    f"Adventure may not exist, not belong to user, or already be complete. Response: {response}"
                )
                return False
        except Exception as e:
            logger.error(
                f"Error abandoning adventure {adventure_id} for user {user_id}: {str(e)}"
            )
            return False

    async def cleanup_expired_adventures(self) -> int:
        """
        Mark adventures older than 30 days as complete (is_complete = True).
        This replaces the previous `cleanup_expired` which deleted records.
        Optionally, a 'completion_reason' could be set.

        Returns:
            int: Number of expired records marked as complete.
        """
        try:
            expiration_time = datetime.now() - timedelta(days=30)
            logger.info(
                f"Cleaning up adventures not updated since {expiration_time.isoformat()}"
            )

            # Consider adding a 'completion_reason' field to the table in a future migration
            # update_payload = {"is_complete": True, "completion_reason": "expired_30_days"}
            update_payload = {"is_complete": True}

            response = (
                self.supabase.table("adventures")
                .update(update_payload)
                .lt("updated_at", expiration_time.isoformat())
                .eq("is_complete", False)  # Only target incomplete adventures
                .execute()
            )

            updated_count = len(response.data) if response.data else 0

            if updated_count > 0:
                logger.info(f"Marked {updated_count} expired adventures as complete.")
            else:
                logger.info("No expired adventures found to mark as complete.")
            return updated_count

        except Exception as e:
            logger.error(
                f"Error cleaning up expired adventures by marking as complete: {str(e)}"
            )
            return 0

    async def cleanup_expired(self) -> int:
        """
        DEPRECATED: This method previously deleted adventures older than 1 hour.
        It is replaced by `cleanup_expired_adventures` which marks them as complete after 30 days.
        Keeping the method signature for now to avoid breaking calls if any, but it will do nothing.
        Consider removing this method in a future refactor.

        Returns:
            int: Always 0.
        """
        logger.warning(
            "DEPRECATED: `cleanup_expired` was called. This method no longer deletes records. Use `cleanup_expired_adventures`."
        )
        return 0
        # Original logic (now deprecated):
        # try:
        #     # Calculate the expiration timestamp (1 hour ago)
        #     expiration_time = datetime.now() - timedelta(hours=1)
        #
        #     # Delete expired records from Supabase
        #     response = (
        #         self.supabase.table("adventures")
        #         .delete()
        #         .lt("created_at", expiration_time.isoformat())
        #         .execute()
        #     )
        #
        #     # Count the number of deleted records
        #     deleted_count = len(response.data) if response.data else 0
        #
        #     if deleted_count > 0:
        #         logger.info(f"Cleaned up {deleted_count} expired states")
        #
        #     return deleted_count
        #
        # except Exception as e:
        #     logger.error(f"Error cleaning up expired states: {str(e)}")
        #     return 0

    async def _abandon_existing_incomplete_adventure(self, user_id: UUID) -> bool:
        """
        Internal helper to find and abandon a user's existing incomplete adventure.
        """
        logger.info(
            f"Checking for existing incomplete adventure for user {user_id} to abandon."
        )
        current_adventure_details = await self.get_user_current_adventure(user_id)
        if current_adventure_details and current_adventure_details.get("adventure_id"):
            adventure_to_abandon_id = current_adventure_details["adventure_id"]
            logger.info(
                f"Found existing incomplete adventure {adventure_to_abandon_id} for user {user_id}. Attempting to abandon."
            )
            abandoned_successfully = await self.abandon_adventure(
                adventure_to_abandon_id, user_id
            )
            if abandoned_successfully:
                logger.info(
                    f"Successfully abandoned previous adventure {adventure_to_abandon_id} for user {user_id}."
                )
                return True
            else:
                logger.warning(
                    f"Failed to abandon previous adventure {adventure_to_abandon_id} for user {user_id}."
                )
                return False
        logger.info(
            f"No existing incomplete adventure found for user {user_id} to abandon."
        )
        return True  # No adventure to abandon, so proceed.
