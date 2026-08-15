import logging
from typing import Any, Dict, List, Optional, Tuple

from openai import AuthenticationError, PermissionDeniedError
from pydantic import ValidationError

from app.data.lesson_loader import sample_question
from app.data.story_loader import StoryLoader
from app.models.story import (
    AdventureState,
    ChapterContent,
    ChapterContentValidator,
    ChapterType,
    LessonResponse,
    StoryChoice,
)
from app.services.chapter_manager import ChapterManager
from app.services.llm.base import BaseLLMService
from app.services.llm.factory import LLMServiceFactory

logger = logging.getLogger("story_app")
_llm_service: Optional[BaseLLMService] = None
chapter_manager = ChapterManager()
MAX_CHAPTER_GENERATION_ATTEMPTS = 3


def get_llm_service() -> BaseLLMService:
    """Create the story-generation client only when generation starts."""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMServiceFactory.create_for_use_case("story_generation")
    return _llm_service


def clean_chapter_content(content: str) -> str:
    """Normalize a validated chapter without masking validation failures."""
    cleaned_content = ChapterContentValidator(content=content).content
    if cleaned_content != content:
        logger.info("Content was cleaned by ChapterContentValidator")
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


async def generate_chapter_content_with_retries(
    story_config: Dict[str, Any],
    state: AdventureState,
    chapter_type: ChapterType,
    question: Optional[Dict[str, Any]],
    current_chapter_number: int,
    previous_lessons: Optional[List[LessonResponse]] = None,
    max_attempts: int = MAX_CHAPTER_GENERATION_ATTEMPTS,
) -> ChapterContent:
    """Generate a structured chapter, retrying any generation or validation error."""
    attempt_error: Optional[Exception] = None
    retry_context: Optional[Dict[str, str]] = None

    for attempt in range(1, max_attempts + 1):
        try:
            generated = await get_llm_service().generate_structured_chapter(
                story_config=story_config,
                state=state,
                question=question,
                previous_lessons=previous_lessons or [],
                context=retry_context,
            )
            cleaned_content = clean_chapter_content(generated.content)

            if chapter_type == ChapterType.LESSON and question:
                story_choices = create_lesson_choices(question)
            elif chapter_type in (ChapterType.STORY, ChapterType.REFLECT):
                if len(generated.choices) != 3:
                    raise ValueError(
                        f"{chapter_type.value.capitalize()} chapters must have "
                        "exactly 3 choices"
                    )
                story_choices = [
                    StoryChoice(
                        text=choice_text,
                        next_chapter=f"chapter_{current_chapter_number}_{index}",
                    )
                    for index, choice_text in enumerate(generated.choices)
                ]
            else:
                if generated.choices:
                    raise ValueError(
                        f"{chapter_type.value.capitalize()} chapters cannot have choices"
                    )
                story_choices = []

            return ChapterContent(content=cleaned_content, choices=story_choices)
        except (AuthenticationError, PermissionDeniedError):
            logger.exception(
                "OpenAI credentials cannot generate story content; aborting without retry"
            )
            raise
        except Exception as exc:
            attempt_error = exc
            if isinstance(exc, (ValidationError, ValueError)):
                retry_context = {
                    "validation_feedback": (
                        "The previous response failed the chapter output contract. "
                        "Regenerate it from scratch. Put only narrative prose in "
                        "`content`; for story or reflect chapters, put exactly three "
                        "distinct, complete choices in `choices` with no labels, "
                        "numbering, brackets, placeholders, or <CHOICES> markup."
                    )
                }
            logger.warning(
                "Chapter generation attempt %s/%s failed validation: %s",
                attempt,
                max_attempts,
                exc,
                exc_info=True,
            )

    raise ValueError(
        "Failed to generate valid structured chapter content after "
        f"{max_attempts} attempts"
    ) from attempt_error


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
