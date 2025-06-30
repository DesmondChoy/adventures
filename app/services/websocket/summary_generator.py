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
    response_generator = await llm_service.generate_with_prompt(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
    )
    async for chunk in response_generator:
        summary_content += chunk

    logger.info(
        "Generated fallback summary content",
        extra={"content_length": len(summary_content)},
    )
    return summary_content


# Import stream_summary_content from stream_handler
from .stream_handler import stream_summary_content  # noqa: F401