"""
Feedback Service
Handles storing and retrieving user feedback from Supabase.
"""

import os
import logging
from typing import Optional
from uuid import UUID

from supabase import create_client, Client as SupabaseClient
from supabase.lib.client_options import ClientOptions
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


class FeedbackService:
    """
    Service for managing user feedback in Supabase.
    Follows the same pattern as TelemetryService.
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
            options = ClientOptions(
                persist_session=False, auto_refresh_token=False
            )
            self.supabase: SupabaseClient = create_client(
                supabase_url, supabase_key, options
            )
            logger.info("FeedbackService initialized with Supabase client.")
        except Exception as e:
            logger.error(
                f"Failed to initialize Supabase client in FeedbackService: {e}"
            )
            raise

    async def store_feedback(
        self,
        adventure_id: UUID,
        rating: str,
        user_id: Optional[UUID] = None,
        client_uuid: Optional[str] = None,
        feedback_text: Optional[str] = None,
        contact_info: Optional[str] = None,
        chapter_number: int = 5,
    ) -> Optional[dict]:
        """
        Store user feedback in the database.

        Args:
            adventure_id: UUID of the current adventure
            rating: 'positive' or 'negative'
            user_id: UUID of authenticated user (None for guests)
            client_uuid: Client UUID for guest users
            feedback_text: Optional text feedback (for negative ratings)
            contact_info: Optional contact info (for guest negative ratings)
            chapter_number: Chapter number when feedback was given (default 5)

        Returns:
            The created feedback record, or None if failed
        """
        if rating not in ('positive', 'negative'):
            logger.warning(f"Invalid rating value: {rating}")
            return None

        record = {
            "adventure_id": str(adventure_id),
            "rating": rating,
            "user_id": str(user_id) if user_id else None,
            "client_uuid": client_uuid,
            "feedback_text": feedback_text,
            "contact_info": contact_info,
            "chapter_number": chapter_number,
            "environment": os.getenv("APP_ENVIRONMENT", "unknown"),
        }

        try:
            response = self.supabase.table("user_feedback").insert(record).execute()

            if response.data:
                logger.info(
                    f"Feedback stored successfully. ID: {response.data[0].get('id')}, "
                    f"Rating: {rating}, User: {user_id or client_uuid}"
                )
                return response.data[0]
            else:
                logger.warning(
                    f"Feedback stored but no data returned. Response: {response}"
                )
                return None

        except Exception as e:
            logger.error(f"Error storing feedback: {e}")
            return None

    async def has_user_given_feedback(
        self,
        user_id: Optional[UUID] = None,
        client_uuid: Optional[str] = None,
    ) -> bool:
        """
        Check if a user has ever given feedback (for "once per user" logic).

        Args:
            user_id: UUID of authenticated user
            client_uuid: Client UUID for guest users

        Returns:
            True if user has given feedback before, False otherwise
        """
        if not user_id and not client_uuid:
            logger.warning("No user_id or client_uuid provided for feedback check")
            return False

        try:
            # Build query based on what identifier we have
            query = self.supabase.table("user_feedback").select("id")

            if user_id:
                # For authenticated users, check by user_id
                query = query.eq("user_id", str(user_id))
            else:
                # For guest users, check by client_uuid
                query = query.eq("client_uuid", client_uuid)

            # We only need to check if any record exists
            query = query.limit(1)

            response = query.execute()

            has_feedback = bool(response.data and len(response.data) > 0)
            logger.debug(
                f"Feedback check for user_id={user_id}, client_uuid={client_uuid}: {has_feedback}"
            )
            return has_feedback

        except Exception as e:
            logger.error(f"Error checking user feedback history: {e}")
            # On error, assume no feedback to avoid blocking the user
            return False


# Lazy instantiation to avoid environment variable loading issues during import
_feedback_service = None


def get_feedback_service() -> FeedbackService:
    """Get or create the feedback service instance."""
    global _feedback_service
    if _feedback_service is None:
        _feedback_service = FeedbackService()
    return _feedback_service
