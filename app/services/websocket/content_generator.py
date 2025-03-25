from typing import Dict, Any, Optional, Tuple, List
import logging
import re

from app.models.story import (
    ChapterType,
    ChapterContent, 
    ChapterContentValidator,
    LessonResponse, 
    StoryChoice,
    AdventureState,
    ChapterData,
)
from app.services.llm import LLMService
from app.services.chapter_manager import ChapterManager
from app.services.llm.prompt_engineering import build_summary_chapter_prompt
from app.data.story_loader import StoryLoader
from app.init_data import sample_question

logger = logging.getLogger("story_app")
llm_service = LLMService()
chapter_manager = ChapterManager()


def clean_chapter_content(content: str) -> str:
    """Clean chapter content using Pydantic validator or regex fallback."""
    try:
        cleaned_content = ChapterContentValidator(content=content).content
        if cleaned_content != content:
            logger.info(
                "Content was cleaned by ChapterContentValidator"
            )
        return cleaned_content.strip()
    except Exception as e:
        logger.error(f"Error in Pydantic validation: {e}")
        # Fallback to regex if Pydantic validation fails
        cleaned_content = re.sub(
            r"^(?:#{1,6}\s+)?chapter(?:\s+(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten))?:?\s*",
            "",
            content,
            flags=re.IGNORECASE,
        )
        logger.debug("Fallback to regex cleaning")
        return cleaned_content.strip()


async def generate_chapter(
    story_category: str,
    lesson_topic: str,
    state: AdventureState,
) -> Tuple[ChapterContent, Optional[dict]]:
    """Generate a complete chapter with content and choices.

    Args:
        story_category: The story category
        lesson_topic: The lesson topic
        state: The current state

    Returns:
        Tuple of (ChapterContent, Optional[dict])
    """
    # Load story configuration using StoryLoader
    story_config = await load_story_config(story_category)

    # Get chapter type
    current_chapter_number = len(state.chapters) + 1
    chapter_type = state.planned_chapter_types[current_chapter_number - 1]
    if not isinstance(chapter_type, ChapterType):
        chapter_type = ChapterType(chapter_type)

    # Initialize variables
    question = None
    previous_lessons = collect_previous_lessons(state)

    # Load new question if at lesson chapter
    if chapter_type == ChapterType.LESSON:
        question = await load_lesson_question(lesson_topic, state)

    # Generate story content
    story_content = await generate_story_content(story_config, state, question, previous_lessons)

    # Extract choices based on chapter type and get cleaned content without choices section
    story_choices, cleaned_content = await extract_story_choices(chapter_type, story_content, question, current_chapter_number)

    # Debug output for choices
    logger.debug("\n=== DEBUG: Story Choices ===")
    for i, choice in enumerate(story_choices, 1):
        logger.debug(f"Choice {i}: {choice.text} (next_chapter: {choice.next_chapter})")
    
    # Return cleaned content (without choices section) in the ChapterContent
    return ChapterContent(content=cleaned_content, choices=story_choices), question


async def load_story_config(story_category: str) -> Dict[str, Any]:
    """Load story configuration from StoryLoader."""
    try:
        loader = StoryLoader()
        story_data = loader.load_all_stories()
        return story_data["story_categories"][story_category]
    except Exception as e:
        logger.error(f"Error loading story data: {str(e)}")
        raise ValueError(f"Failed to load story data: {str(e)}")


def collect_previous_lessons(state: AdventureState) -> List[LessonResponse]:
    """Collect previous lesson responses from chapter history."""
    previous_lessons = [
        LessonResponse(
            question=chapter.response.question,
            chosen_answer=chapter.response.chosen_answer,
            is_correct=chapter.response.is_correct,
        )
        for chapter in state.chapters
        if chapter.chapter_type == ChapterType.LESSON and chapter.response
    ]

    logger.debug("\n=== DEBUG: Previous Lessons Collection ===")
    logger.debug(f"Total chapters: {len(state.chapters)}")
    logger.debug(f"Number of previous lessons: {len(previous_lessons)}")

    if previous_lessons:
        logger.debug("\nLesson details:")
        for i, pl in enumerate(previous_lessons, 1):
            logger.debug(f"Lesson {i}:")
            logger.debug(f"Question: {pl.question['question']}")
            logger.debug(f"Chosen Answer: {pl.chosen_answer}")
            logger.debug(f"Is Correct: {pl.is_correct}")
    else:
        logger.debug("No previous lessons found")
    logger.debug("=========================================\n")
    
    return previous_lessons


async def load_lesson_question(lesson_topic: str, state: AdventureState) -> Dict[str, Any]:
    """Load a lesson question for LESSON chapters."""
    try:
        used_questions = [
            chapter.response.question["question"]
            for chapter in state.chapters
            if chapter.chapter_type == ChapterType.LESSON and chapter.response
        ]

        # Get difficulty from state metadata if available (for future difficulty toggle)
        difficulty = state.metadata.get("difficulty", "Reasonably Challenging")

        # Sample question with optional difficulty parameter
        question = sample_question(
            lesson_topic, exclude_questions=used_questions, difficulty=difficulty
        )

        logger.debug(f"DEBUG: Selected question: {question['question']}")
        logger.debug(f"DEBUG: Answers: {question['answers']}")
        logger.debug(
            f"DEBUG: Difficulty: {question.get('difficulty', 'Not specified')}"
        )
        return question
    except ValueError as e:
        logger.error(f"Error sampling question: {e}")
        raise


async def generate_story_content(
    story_config: Dict[str, Any],
    state: AdventureState,
    question: Optional[Dict[str, Any]],
    previous_lessons: List[LessonResponse]
) -> str:
    """Generate story content from the LLM."""
    try:
        story_content = ""
        async for chunk in llm_service.generate_chapter_stream(
            story_config,
            state,
            question,
            previous_lessons,
        ):
            story_content += chunk

        story_content = clean_generated_content(story_content)
        return story_content
    except Exception as e:
        logger.error("\n=== ERROR: LLM Request Failed ===")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error message: {str(e)}")
        logger.error("===============================\n")
        raise


def clean_generated_content(content: str) -> str:
    """Clean generated content using Pydantic validator or regex fallback."""
    try:
        validated_content = ChapterContentValidator(content=content).content
        if validated_content != content:
            logger.info("Content was cleaned by ChapterContentValidator")
            logger.debug(f"Original content started with: {content[:50]}...")
            logger.debug(
                f"Cleaned content starts with: {validated_content[:50]}..."
            )
        return validated_content
    except Exception as e:
        logger.error(f"Error in Pydantic validation: {e}")
        # Fallback to regex if Pydantic validation fails
        cleaned_content = re.sub(
            r"^(?:#{1,6}\s+)?chapter(?:\s+(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten))?:?\s*",
            "",
            content,
            flags=re.IGNORECASE,
        )
        logger.debug("Fallback to regex cleaning after Pydantic validation failure")
        
        # Check for dialogue formatting issues in the generated content
        if re.match(
            r"^(chirped|said|whispered|shouted|called|murmured|exclaimed|replied|asked|answered|responded)\b",
            cleaned_content.strip(),
        ):
            logger.warning(
                "Generated content starts with dialogue verb - possible missing character name"
            )
        
        return cleaned_content


async def extract_story_choices(
    chapter_type: ChapterType,
    story_content: str,
    question: Optional[Dict[str, Any]],
    current_chapter_number: int
) -> Tuple[List[StoryChoice], str]:
    """Extract story choices based on chapter type.
    
    Returns:
        Tuple containing (list of story choices, cleaned story content without choices section)
    """
    # Extract choices based on chapter type
    if chapter_type == ChapterType.LESSON and question:
        return create_lesson_choices(question), story_content
    elif chapter_type == ChapterType.STORY or chapter_type == ChapterType.REFLECT:
        return await extract_regular_choices(chapter_type, story_content, current_chapter_number)
    else:  # CONCLUSION chapter
        return [], story_content  # No choices for conclusion chapters


def create_lesson_choices(question: Dict[str, Any]) -> List[StoryChoice]:
    """Create choices for a lesson chapter from question answers."""
    story_choices = []
    for answer in question["answers"]:
        story_choices.append(
            StoryChoice(
                text=answer["text"],
                next_chapter="correct"
                if answer["is_correct"]
                else f"wrong{len(story_choices) + 1}",
            )
        )
    return story_choices


async def extract_regular_choices(
    chapter_type: ChapterType,
    story_content: str,
    current_chapter_number: int
) -> Tuple[List[StoryChoice], str]:
    """Extract choices from STORY or REFLECT chapter content.
    
    Returns:
        Tuple containing (list of story choices, cleaned story content without choices section)
    """
    logger.debug(f"Extracting choices for {chapter_type.value} chapter")

    # Add more detailed logging for REFLECT chapters
    if chapter_type == ChapterType.REFLECT:
        logger.debug("Processing REFLECT chapter choices")
        logger.debug(f"Content length: {len(story_content)}")
        # Log the last 200 characters to see if <CHOICES> section is present
        logger.debug(
            f"Content tail: {story_content[-200:] if len(story_content) > 200 else story_content}"
        )
    
    clean_content = story_content
    try:
        # First extract the choices section
        choices_match = re.search(
            r"<CHOICES>\s*(.*?)\s*</CHOICES>",
            story_content,
            re.DOTALL | re.IGNORECASE,
        )

        if not choices_match:
            logger.error(
                "Could not find choice markers in story content. Raw content:"
            )
            logger.error(story_content)
            raise ValueError("Could not find choice markers in story content")

        # Extract choices text and clean up story content
        choices_text = choices_match.group(1).strip()
        clean_content = story_content[: choices_match.start()].strip()
        # Clean the content
        clean_content = clean_generated_content(clean_content)

        # Extract choices from the choices text
        choices = parse_choice_text(choices_text)

        if not choices:
            logger.error(f"No choices found in choices text. Raw choices text:")
            logger.error(choices_text)
            raise ValueError("No choices found in story content")

        if len(choices) != 3:
            logger.warning(
                f"Expected 3 choices but found {len(choices)}. Raw choices text:"
            )
            logger.warning(choices_text)
            # If we found at least one choice, use what we have rather than failing
            if choices:
                logger.info("Proceeding with available choices")
            else:
                raise ValueError("Must have at least one valid choice")

        story_choices = [
            StoryChoice(
                text=choice_text,
                next_chapter=f"chapter_{current_chapter_number}_{i}",
            )
            for i, choice_text in enumerate(choices)
        ]
        
        return story_choices, clean_content
    except Exception as e:
        logger.error(f"Error parsing choices: {e}")
        fallback_choices = [
            StoryChoice(
                text=f"Continue with option {i + 1}",
                next_chapter=f"chapter_{current_chapter_number}_{i}",
            )
            for i in range(3)
        ]
        return fallback_choices, clean_content


def parse_choice_text(choices_text: str) -> List[str]:
    """Parse the choices text to extract individual choices."""
    choices = []

    # Try multi-line format first (within choices section)
    choice_pattern = r"Choice\s*([ABC])\s*:\s*([^\n]+)"
    matches = re.finditer(
        choice_pattern, choices_text, re.IGNORECASE | re.MULTILINE
    )
    for match in matches:
        choices.append(match.group(2).strip())

    # If no matches found, try single-line format (still within choices section)
    if not choices:
        single_line_pattern = (
            r"Choice\s*[ABC]\s*:\s*([^.]+(?:\.\s*(?=Choice\s*[ABC]\s*:|$))?)"
        )
        matches = re.finditer(single_line_pattern, choices_text, re.IGNORECASE)
        for match in matches:
            choices.append(match.group(1).strip())
    
    return choices


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