"""
Chapter processing functionality for extracting and generating chapter summaries.
"""

import logging
import asyncio
from typing import Dict, Any, List

from app.models.story import AdventureState, ChapterType
from app.services.chapter_manager import ChapterManager
from app.services.summary.helpers import ChapterTypeHelper

logger = logging.getLogger("summary_service.chapter_processor")


class ChapterProcessor:
    """Processes chapters to extract summaries and ensure proper chapter types."""
    
    @staticmethod
    def ensure_conclusion_chapter(state: AdventureState) -> AdventureState:
        """Ensures the last chapter is properly identified as a CONCLUSION chapter.

        Args:
            state: The adventure state to process

        Returns:
            Updated adventure state with proper CONCLUSION chapter
        """
        # Log all chapters for debugging
        logger.info(f"Total chapters: {len(state.chapters)}")

        # If no chapters, return the state as is
        if not state.chapters:
            logger.warning("No chapters found in state")
            return state

        # Sort chapters by chapter_number to ensure proper ordering
        sorted_chapters = sorted(state.chapters, key=lambda ch: ch.chapter_number)

        # Track if we've found a CONCLUSION chapter
        has_conclusion = False

        # First check if we have a chapter with type CONCLUSION
        for ch in sorted_chapters:
            if ChapterTypeHelper.is_conclusion_chapter(ch.chapter_type):
                has_conclusion = True
                logger.info(f"Found explicit CONCLUSION chapter: {ch.chapter_number}")

                # Ensure chapter type is set to the enum value
                if ch.chapter_type != ChapterType.CONCLUSION:
                    logger.info(
                        f"Converting chapter {ch.chapter_number} type from '{ch.chapter_type}' to ChapterType.CONCLUSION"
                    )
                    ch.chapter_type = ChapterType.CONCLUSION

        # If no conclusion chapter was found, mark the last chapter as CONCLUSION
        if not has_conclusion and sorted_chapters:
            # Get the last chapter by number (not index)
            last_chapter = sorted_chapters[-1]

            logger.info(
                f"No CONCLUSION chapter found. Setting last chapter {last_chapter.chapter_number} as CONCLUSION (was {last_chapter.chapter_type})"
            )
            last_chapter.chapter_type = ChapterType.CONCLUSION
            has_conclusion = True

        # Final verification - Check if we successfully identified a CONCLUSION chapter
        conclusion_chapter = None
        for ch in sorted_chapters:
            if ch.chapter_type == ChapterType.CONCLUSION:
                conclusion_chapter = ch
                break

        if conclusion_chapter:
            logger.info(
                f"Verified CONCLUSION chapter {conclusion_chapter.chapter_number} is properly set"
            )
        else:
            logger.warning("Failed to set CONCLUSION chapter. Using fallback approach.")
            # Ultimate fallback - just set the last chapter to CONCLUSION
            if sorted_chapters:
                sorted_chapters[-1].chapter_type = ChapterType.CONCLUSION
                logger.info(
                    f"Set last chapter {sorted_chapters[-1].chapter_number} as CONCLUSION using fallback"
                )

        return state
    
    @staticmethod
    def extract_chapter_summaries(state: AdventureState) -> List[Dict[str, Any]]:
        """Extract chapter summaries with robust fallbacks.

        Args:
            state: The adventure state to process

        Returns:
            List of chapter summary objects
        """
        logger.info("\n=== Extracting Chapter Summaries ===")
        chapter_summaries = []

        # Check if we have stored chapter summaries
        existing_summaries = getattr(state, "chapter_summaries", [])
        existing_titles = getattr(state, "summary_chapter_titles", [])

        logger.info(
            f"Found {len(existing_summaries)} existing summaries and {len(existing_titles)} existing titles"
        )

        # Ensure the last chapter is marked as CONCLUSION
        try:
            # This ensures the CONCLUSION chapter is properly identified before processing
            state = ChapterProcessor.ensure_conclusion_chapter(state)
            logger.info("Ensured CONCLUSION chapter is properly identified")
        except Exception as e:
            logger.error(f"Error ensuring CONCLUSION chapter: {str(e)}")

        # Process each chapter in chapter number order
        for chapter in sorted(state.chapters, key=lambda x: x.chapter_number):
            chapter_number = chapter.chapter_number
            logger.info(
                f"Processing chapter {chapter_number} of type {chapter.chapter_type}"
            )

            # Get or generate summary
            summary_text = ChapterProcessor._get_chapter_summary(
                chapter, chapter_number, existing_summaries
            )

            # Get or generate title
            title = ChapterProcessor._get_chapter_title(
                chapter_number, existing_titles, summary_text, chapter.chapter_type
            )

            # Get chapter type as string in a consistent format
            chapter_type_str = ChapterTypeHelper.get_chapter_type_string(chapter.chapter_type)

            # Validate chapter_type_str against known types
            valid_types = ["story", "lesson", "reflect", "conclusion", "summary"]
            if chapter_type_str not in valid_types:
                logger.warning(
                    f"Invalid chapter type: {chapter_type_str}, defaulting to 'story'"
                )
                chapter_type_str = "story"

            # Special case handling for the last chapter
            if chapter_number == len(state.chapters):
                logger.info(f"Chapter {chapter_number} is the last chapter")
                # If the last chapter isn't already marked as conclusion, consider marking it
                if (
                    chapter_type_str != "conclusion" and chapter_number >= 9
                ):  # Only consider if chapter 9+
                    logger.info(f"Setting last chapter {chapter_number} as CONCLUSION type")
                    chapter_type_str = "conclusion"

            # Create summary object with snake_case keys (will be converted to camelCase at API boundary)
            summary_obj = {
                "number": chapter_number,
                "title": title,
                "summary": summary_text,
                "chapter_type": chapter_type_str,
            }

            logger.info(
                f"Created summary object for chapter {chapter_number} with type {chapter_type_str}"
            )
            chapter_summaries.append(summary_obj)

        # Final confirmation
        logger.info(f"Successfully extracted {len(chapter_summaries)} chapter summaries")
        return chapter_summaries
    
    @staticmethod
    def _get_chapter_summary(chapter, chapter_number, existing_summaries):
        """Get or generate a summary for a chapter."""
        if chapter_number <= len(existing_summaries):
            summary_text = existing_summaries[chapter_number - 1]
            logger.info(
                f"Using existing summary for chapter {chapter_number}: {summary_text[:50]}..."
            )
            return summary_text
            
        # Try to use ChapterManager to generate a proper summary if we have access to it
        try:
            # Create a new instance of ChapterManager
            chapter_manager = ChapterManager()

            # Check if we can use the async function
            if asyncio.get_event_loop().is_running():
                # We're in an async context, can directly use the async function
                logger.info(
                    f"Generating proper summary for chapter {chapter_number} using ChapterManager"
                )
                summary_result = asyncio.create_task(
                    chapter_manager.generate_chapter_summary(chapter.content)
                )
                # Wait for the result (this is safe in an async context)
                summary_result = asyncio.get_event_loop().run_until_complete(
                    summary_result
                )
                if isinstance(summary_result, dict):
                    summary_text = summary_result.get("summary", "")
                    logger.info(
                        f"Generated summary using ChapterManager: {summary_text[:50]}..."
                    )
                    return summary_text
            else:
                # We're not in an async context, fall back to content-based summary
                logger.warning("Not in async context, cannot use ChapterManager")
                
        except Exception as e:
            logger.warning(
                f"Error generating summary with ChapterManager: {str(e)}"
            )
            
        # Generate simple summary from content (fallback)
        summary_text = (
            f"{chapter.content[:150]}..."
            if len(chapter.content) > 150
            else chapter.content
        )
        logger.info(
            f"Generated fallback summary for chapter {chapter_number}: {summary_text[:50]}..."
        )
        return summary_text
    
    @staticmethod
    def _get_chapter_title(chapter_number, existing_titles, summary_text, chapter_type):
        """Get or generate a title for a chapter."""
        # Use existing title if available
        if chapter_number <= len(existing_titles):
            title = existing_titles[chapter_number - 1]
            logger.info(f"Using existing title for chapter {chapter_number}: {title}")
            return title
            
        # Try extracting title from summary (if it has title: content format)
        if ":" in summary_text and len(summary_text.split(":", 1)[0]) < 50:
            title = summary_text.split(":", 1)[0].strip()
            logger.info(f"Extracted title from summary: {title}")
            return title
            
        # Generate title based on chapter type
        chapter_type_str = ChapterTypeHelper.get_chapter_type_string(chapter_type).capitalize()
        title = f"Chapter {chapter_number}: {chapter_type_str}"
        logger.info(f"Generated title based on chapter type: {title}")
        return title
    
    @staticmethod
    async def process_stored_chapter_summaries(state_data: Dict[str, Any]) -> None:
        """Process chapters to ensure all have summaries."""
        # Sort chapters by chapter number to ensure correct order
        sorted_chapters = sorted(
            state_data.get("chapters", []), key=lambda x: x.get("chapter_number", 0)
        )
        
        if not sorted_chapters:
            return

        # Import ChapterManager for summary generation
        chapter_manager = ChapterManager()

        for chapter in sorted_chapters:
            chapter_number = chapter.get("chapter_number", 0)
            chapter_type = str(chapter.get("chapter_type", "")).lower()

            # Check if we need to generate a summary for this chapter
            if len(state_data["chapter_summaries"]) < chapter_number:
                logger.info(f"Missing summary for chapter {chapter_number} ({chapter_type})")

                # Add placeholder summaries for any gaps
                while len(state_data["chapter_summaries"]) < chapter_number - 1:
                    state_data["chapter_summaries"].append("Chapter summary not available")
                    # Also add placeholder titles
                    if len(state_data["summary_chapter_titles"]) < len(state_data["chapter_summaries"]):
                        state_data["summary_chapter_titles"].append(
                            f"Chapter {len(state_data['summary_chapter_titles']) + 1}"
                        )

                # Generate summary for this chapter
                try:
                    await ChapterProcessor._generate_and_store_chapter_summary(
                        chapter_manager, chapter, chapter_number, chapter_type, sorted_chapters, state_data
                    )
                except Exception as e:
                    logger.error(f"Error generating summary for chapter {chapter_number}: {e}")
                    # Add fallback summary and title
                    state_data["chapter_summaries"].append(f"Summary for Chapter {chapter_number}")
                    state_data["summary_chapter_titles"].append(
                        f"Chapter {chapter_number}: {chapter_type.capitalize()}"
                    )
                    logger.info(f"Added fallback summary for chapter {chapter_number}")

        logger.info(f"Processed {len(sorted_chapters)} chapters, ensuring all have summaries")
        logger.info(f"Final chapter_summaries count: {len(state_data['chapter_summaries'])}")
        logger.info(f"Final summary_chapter_titles count: {len(state_data['summary_chapter_titles'])}")
    
    @staticmethod 
    async def _generate_and_store_chapter_summary(
        chapter_manager, chapter, chapter_number, chapter_type, sorted_chapters, state_data
    ):
        """Generate and store a summary for a chapter."""
        # Get choice context from next chapter's response if available
        choice_text = None
        choice_context = ""

        # For non-conclusion chapters, try to find choice from next chapter
        if chapter_type != "conclusion" and chapter_number < len(sorted_chapters):
            next_chapter = sorted_chapters[chapter_number]
            if next_chapter and next_chapter.get("response"):
                response = next_chapter.get("response", {})
                if response.get("choice_text"):
                    choice_text = response.get("choice_text")
                elif response.get("chosen_answer"):
                    choice_text = response.get("chosen_answer")
                    choice_context = (
                        " (Correct answer)" if response.get("is_correct") else " (Incorrect answer)"
                    )

        # For conclusion chapter, use placeholder choice
        if chapter_type == "conclusion":
            choice_text = "End of story"
            choice_context = ""
            logger.info(f"Using placeholder choice for CONCLUSION chapter")

        # Generate the summary
        logger.info(f"Generating summary for chapter {chapter_number}")
        summary_result = await chapter_manager.generate_chapter_summary(
            chapter.get("content", ""), choice_text, choice_context
        )

        # Extract title and summary
        title = summary_result.get(
            "title", f"Chapter {chapter_number}: {chapter_type.capitalize()}"
        )
        summary = summary_result.get("summary", "Summary not available")

        # Add to state data
        state_data["chapter_summaries"].append(summary)
        state_data["summary_chapter_titles"].append(title)

        logger.info(f"Generated summary for chapter {chapter_number}: {summary[:50]}...")
        logger.info(f"Generated title for chapter {chapter_number}: {title}")