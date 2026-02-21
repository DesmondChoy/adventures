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
)
from app.services.llm.factory import LLMServiceFactory
from app.services.chapter_manager import ChapterManager
from app.data.story_loader import StoryLoader
from app.data.lesson_loader import sample_question

logger = logging.getLogger("story_app")
llm_service = LLMServiceFactory.create_for_use_case("story_generation")
chapter_manager = ChapterManager()
MAX_CHAPTER_GENERATION_ATTEMPTS = 3


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

    chapter_content = await generate_chapter_content_with_retries(
        story_config=story_config,
        state=state,
        chapter_type=chapter_type,
        question=question,
        current_chapter_number=current_chapter_number,
        previous_lessons=previous_lessons,
    )

    # Debug output for choices
    logger.debug("\n=== DEBUG: Story Choices ===")
    for i, choice in enumerate(chapter_content.choices, 1):
        logger.debug(f"Choice {i}: {choice.text} (next_chapter: {choice.next_chapter})")
    
    # Return cleaned content (without choices section) in the ChapterContent
    return chapter_content, question


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


async def generate_chapter_content_with_retries(
    story_config: Dict[str, Any],
    state: AdventureState,
    chapter_type: ChapterType,
    question: Optional[Dict[str, Any]],
    current_chapter_number: int,
    previous_lessons: Optional[List[LessonResponse]] = None,
    max_attempts: int = MAX_CHAPTER_GENERATION_ATTEMPTS,
) -> ChapterContent:
    """Generate chapter content, retrying until valid choices are produced."""
    attempt_error: Optional[Exception] = None

    for attempt in range(1, max_attempts + 1):
        story_content = await generate_story_content(
            story_config, state, question, previous_lessons or []
        )
        try:
            story_choices, cleaned_content = await extract_story_choices(
                chapter_type, story_content, question, current_chapter_number
            )
            return ChapterContent(content=cleaned_content, choices=story_choices)
        except Exception as exc:
            attempt_error = exc
            logger.warning(
                "Chapter generation attempt %s/%s failed choice validation: %s",
                attempt,
                max_attempts,
                exc,
            )

    raise ValueError(
        "Failed to generate chapter content with valid choices after "
        f"{max_attempts} attempts"
    ) from attempt_error


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
            logger.error(
                f"Expected exactly 3 choices but found {len(choices)}. Raw choices text:"
            )
            logger.error(choices_text)
            raise ValueError("Story chapters must end with exactly 3 choices")

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
        raise


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
