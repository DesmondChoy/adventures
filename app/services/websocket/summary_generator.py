from typing import List
import logging

from app.models.story import ChapterType, ChapterData, AdventureState
from app.services.llm.factory import LLMServiceFactory
from app.services.llm.prompt_engineering import build_summary_chapter_prompt

logger = logging.getLogger("story_app")
llm_service = LLMServiceFactory.create_for_use_case("summary_generation")


async def generate_summary_content(state: AdventureState) -> str:
    """Generate summary content for the SUMMARY chapter.

    This function uses the stored chapter summaries to create a chronological
    recap of the adventure, along with a learning report showing all questions
    and answers.

    Args:
        state: The current adventure state

    Returns:
        The generated summary content
    """
    try:
        # Check if we have chapter summaries
        if state.chapter_summaries and len(state.chapter_summaries) > 0:
            return build_summary_from_stored_data(state)
        else:
            return await generate_fallback_summary(state)
    except Exception as e:
        logger.error(f"Error generating summary content: {str(e)}")
        # Return a fallback summary if generation fails
        return """# Adventure Summary

## Your Journey Recap
You've completed an amazing educational adventure! Throughout your journey, you explored new worlds, 
made important choices, and learned valuable lessons.

## Learning Report
You answered several educational questions during your adventure. Some were challenging, 
but each one helped you grow and learn.

Thank you for joining us on this learning odyssey!
"""


def build_summary_from_stored_data(state: AdventureState) -> str:
    """Build summary content from stored chapter summaries and questions."""
    logger.info(
        f"Using {len(state.chapter_summaries)} stored chapter summaries for summary content"
    )

    # Create the summary content with chapter summaries
    summary_content = "# Adventure Summary\n\n"

    # Add journey recap section with chapter summaries
    summary_content += "## Your Journey Recap\n\n"

    for i, summary in enumerate(state.chapter_summaries, 1):
        # Get the chapter type for context
        chapter_type = "Unknown"
        if i <= len(state.chapters):
            chapter_type = state.chapters[i - 1].chapter_type.value.capitalize()

        # Get title from summary_chapter_titles if available
        title = f"Chapter {i}"
        if hasattr(state, "summary_chapter_titles") and i <= len(
            state.summary_chapter_titles
        ):
            title = state.summary_chapter_titles[i - 1]

        summary_content += f"### {title} ({chapter_type})\n"
        summary_content += f"{summary}\n\n"

    # Add learning report section
    summary_content += "\n\n# Learning Report\n\n"

    # Get all lesson chapters
    lesson_chapters = [
        chapter
        for chapter in state.chapters
        if chapter.chapter_type == ChapterType.LESSON and chapter.response
    ]

    if lesson_chapters:
        summary_content += build_learning_report(lesson_chapters)
    else:
        summary_content += "You didn't encounter any educational questions in this adventure.\n\n"

    # Add conclusion
    summary_content += "Thank you for joining us on this learning odyssey!\n"

    logger.info(
        "Generated summary content from stored summaries",
        extra={"content_length": len(summary_content)},
    )
    return summary_content


def build_learning_report(lesson_chapters: List[ChapterData]) -> str:
    """Build the learning report section of the summary."""
    report = ""
    for i, chapter in enumerate(lesson_chapters, 1):
        lesson_response = chapter.response
        question = lesson_response.question["question"]
        chosen_answer = lesson_response.chosen_answer
        is_correct = lesson_response.is_correct

        # Find the correct answer
        correct_answer = next(
            answer["text"]
            for answer in lesson_response.question["answers"]
            if answer["is_correct"]
        )

        # Get explanation if available
        explanation = lesson_response.question.get("explanation", "")

        report += f"### Question {i}: {question}\n"
        report += f"- Your answer: {chosen_answer} "
        report += f"({'✓ Correct' if is_correct else '✗ Incorrect'})\n"

        if not is_correct:
            report += f"- Correct answer: {correct_answer}\n"

        if explanation:
            report += f"- Explanation: {explanation}\n"

        report += "\n"
    
    return report


async def generate_fallback_summary(state: AdventureState) -> str:
    """Generate a fallback summary using the LLM when no stored summaries are available."""
    logger.warning(
        "No chapter summaries available, falling back to LLM-generated summary"
    )
    # Fall back to the original method if no summaries are available
    system_prompt, user_prompt = build_summary_chapter_prompt(state)

    # Generate the summary content
    summary_content = ""
    async for chunk in llm_service.generate_with_prompt(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
    ):
        summary_content += chunk

    logger.info(
        "Generated fallback summary content",
        extra={"content_length": len(summary_content)},
    )
    return summary_content


async def ensure_all_summaries_exist(state: AdventureState) -> None:
    """Ensure all chapters have summaries, generating missing ones on-demand.
    
    This function checks if any chapter summaries are missing and generates them
    to avoid race conditions in deferred task management.
    
    Args:
        state: The current adventure state
    """
    logger.info(f"Checking summaries for {len(state.chapters)} chapters")
    
    # chapter_summaries is a list, check if we have summaries for all chapters
    missing_chapters = []
    for chapter in state.chapters:
        chapter_index = chapter.chapter_number - 1  # Convert to 0-based index
        
        # Check if we have a summary at this index
        if (not state.chapter_summaries or 
            len(state.chapter_summaries) <= chapter_index or 
            not state.chapter_summaries[chapter_index]):
            missing_chapters.append(chapter)
            logger.info(f"Missing summary for chapter {chapter.chapter_number} (type: {chapter.chapter_type})")
    
    if not missing_chapters:
        logger.info("All chapter summaries already exist")
        return
    
    logger.info(f"Generating {len(missing_chapters)} missing summaries")
    
    # Generate missing summaries using the existing chapter manager function
    from app.services.chapter_manager import ChapterManager
    
    for chapter in missing_chapters:
        try:
            # Use the existing chapter summary generation function
            # For chapters without responses, provide defaults
            chosen_choice = chapter.response.chosen_path if chapter.response else "story_progression"
            choice_context = chapter.response.choice_text if chapter.response else ""
            
            summary_result = await ChapterManager.generate_chapter_summary(
                chapter_content=chapter.content,
                chosen_choice=chosen_choice,
                choice_context=choice_context
            )
            
            # Store in state (same format as regular summary generation)
            chapter_index = chapter.chapter_number - 1  # Convert to 0-based index
            
            # Ensure the lists are large enough
            while len(state.chapter_summaries) <= chapter_index:
                state.chapter_summaries.append("")
            while len(state.summary_chapter_titles) <= chapter_index:
                state.summary_chapter_titles.append("")
            
            # Store the summary and title
            state.chapter_summaries[chapter_index] = summary_result["summary"]
            if "title" in summary_result:
                state.summary_chapter_titles[chapter_index] = summary_result["title"]
            
            logger.info(f"Generated on-demand summary for chapter {chapter.chapter_number}")
            
        except Exception as e:
            logger.error(f"Failed to generate summary for chapter {chapter.chapter_number}: {e}")
            # Store a fallback summary
            chapter_index = chapter.chapter_number - 1
            
            # Ensure the list is large enough for fallback
            while len(state.chapter_summaries) <= chapter_index:
                state.chapter_summaries.append("")
            
            state.chapter_summaries[chapter_index] = f"Chapter {chapter.chapter_number} summary (generated on-demand)"


# Import stream_summary_content from stream_handler
from .stream_handler import stream_summary_content  # noqa: F401