"""
Main service class for managing adventure summaries.
"""

import logging
from typing import Dict, Any, Optional, List

from app.models.story import AdventureState
from app.services.state_storage_service import StateStorageService
from app.services.adventure_state_manager import AdventureStateManager
from app.services.summary.exceptions import StateNotFoundError, SummaryGenerationError
from app.services.summary.dto import AdventureSummaryDTO
from app.services.summary.chapter_processor import ChapterProcessor
from app.services.summary.question_processor import QuestionProcessor
from app.services.summary.stats_processor import StatsProcessor

logger = logging.getLogger("summary_service")


class SummaryService:
    """Service for generating and retrieving adventure summaries."""

    def __init__(self, state_storage_service: StateStorageService):
        """Initialize the summary service.

        Args:
            state_storage_service: Service for storing and retrieving state
        """
        self.state_storage_service = state_storage_service
        self.chapter_processor = ChapterProcessor()
        self.question_processor = QuestionProcessor()
        self.stats_processor = StatsProcessor()

    async def get_adventure_state_from_id(
        self, state_id: Optional[str] = None
    ) -> AdventureState:
        """Retrieves and reconstructs AdventureState from storage or active state.

        Args:
            state_id: Optional ID of the stored state

        Returns:
            Reconstructed AdventureState object

        Raises:
            StateNotFoundError: If state cannot be found or reconstructed
        """
        # Create the adventure state manager
        state_manager = AdventureStateManager()

        # First try to get state from the state manager (active state)
        state = state_manager.get_current_state()

        # If no active state and state_id is provided, try to get from storage
        if not state and state_id:
            logger.info(f"No active state, trying to get stored state: {state_id}")

            # Get the stored state from the storage service
            stored_state = await self.state_storage_service.get_state(state_id)

            if not stored_state:
                logger.warning(f"No stored state found with ID: {state_id}")
                raise StateNotFoundError(
                    "No adventure state found. Please complete an adventure to view the summary."
                )

            try:
                logger.info(f"Retrieved state with ID: {state_id}")
                logger.debug(f"State content keys: {list(stored_state.keys())}")

                # Use the method to reconstruct state from stored data
                state = await state_manager.reconstruct_state_from_storage(stored_state)

                if not state:
                    logger.error("State reconstruction failed")
                    raise StateNotFoundError("Failed to reconstruct adventure state")

                logger.info(f"Successfully reconstructed state with ID: {state_id}")
            except Exception as e:
                logger.error(f"Error reconstructing state: {str(e)}")
                raise StateNotFoundError(f"Error reconstructing state: {str(e)}")

        # If we still don't have a state, return 404
        if not state:
            logger.warning("No active adventure state found")
            raise StateNotFoundError(
                "No adventure state found. Please complete an adventure to view the summary."
            )

        return state

    def ensure_conclusion_chapter(self, state: AdventureState) -> AdventureState:
        """Ensures the last chapter is properly identified as a CONCLUSION chapter."""
        return self.chapter_processor.ensure_conclusion_chapter(state)

    def format_adventure_summary_data(self, state: AdventureState) -> Dict[str, Any]:
        """Transform AdventureState into formatted summary data.

        Args:
            state: The adventure state to process

        Returns:
            Formatted data for the summary view
        """
        try:
            # Log detailed state information for debugging
            logger.info("\n=== Building Adventure Summary Data ===")
            logger.info(f"Total chapters: {len(state.chapters)}")
            logger.info(f"Story length: {state.story_length}")

            # Extract data with fallbacks for missing elements
            chapter_summaries = self.chapter_processor.extract_chapter_summaries(state)
            logger.info(f"Extracted {len(chapter_summaries)} chapter summaries")

            educational_questions = (
                self.question_processor.extract_educational_questions(state)
            )
            logger.info(f"Extracted {len(educational_questions)} educational questions")

            statistics = self.stats_processor.calculate_adventure_statistics(
                state, educational_questions
            )
            logger.info(f"Calculated statistics: {statistics}")

            # Create the DTO
            summary_dto = AdventureSummaryDTO(
                chapter_summaries=chapter_summaries,
                educational_questions=educational_questions,
                statistics=statistics,
            )

            # Return the data in snake_case format
            return summary_dto.to_dict()

        except Exception as e:
            logger.error(f"Error formatting summary data: {e}")
            # Return minimal valid structure on error with snake_case keys
            return {
                "chapter_summaries": [],
                "educational_questions": [
                    {
                        "question": "What did you think of your adventure?",
                        "user_answer": "It was great!",
                        "is_correct": True,
                        "explanation": "We're glad you enjoyed it.",
                    }
                ],
                "statistics": {
                    "chapters_completed": len(state.chapters) if state else 0,
                    "questions_answered": 1,
                    "time_spent": "30 mins",
                    "correct_answers": 1,
                },
            }

    async def store_adventure_state(
        self, state_data: Dict[str, Any], adventure_id: Optional[str] = None
    ) -> str:
        """Store adventure state with enhanced processing.

        Args:
            state_data: The adventure state data to store
            adventure_id: Optional ID of an existing adventure to update

        Returns:
            The ID of the stored state

        Raises:
            SummaryGenerationError: If there was an error processing or storing the state
        """
        try:
            # Log critical fields to help with debugging
            logger.info("Storing adventure state with the following fields:")
            logger.info(f"Chapters count: {len(state_data.get('chapters', []))}")
            logger.info(
                f"Chapter summaries count: {len(state_data.get('chapter_summaries', []))}"
            )
            logger.info(
                f"Summary chapter titles count: {len(state_data.get('summary_chapter_titles', []))}"
            )
            logger.info(
                f"Lesson questions count: {len(state_data.get('lesson_questions', []))}"
            )

            # Ensure chapter_summaries exists
            if not state_data.get("chapter_summaries"):
                state_data["chapter_summaries"] = []
                logger.info("Created empty chapter_summaries array")

            # Ensure summary_chapter_titles exists
            if not state_data.get("summary_chapter_titles"):
                state_data["summary_chapter_titles"] = []
                logger.info("Created empty summary_chapter_titles array")

            # Only generate summaries if they're actually missing
            if state_data.get("chapters") and (
                not state_data.get("chapter_summaries")
                or len(state_data.get("chapter_summaries", []))
                < len(state_data.get("chapters", []))
            ):
                logger.info("Missing chapter summaries detected, generating them now")
                await self.chapter_processor.process_stored_chapter_summaries(
                    state_data
                )
            else:
                logger.info("All chapter summaries already exist, skipping generation")

            # Process lesson questions if needed
            if not state_data.get("lesson_questions"):
                await self.question_processor.process_stored_lesson_questions(
                    state_data
                )

            # Store the enhanced state
            state_id = await self.state_storage_service.store_state(
                state_data, adventure_id=adventure_id
            )
            if adventure_id:
                logger.info(f"Successfully updated enhanced state with ID: {state_id}")
            else:
                logger.info(
                    f"Successfully stored new enhanced state with ID: {state_id}"
                )
            return state_id
        except Exception as e:
            logger.error(f"Error storing adventure state: {str(e)}")
            raise SummaryGenerationError(f"Error storing adventure state: {str(e)}")
