from typing import Any, Dict, Optional, List, Literal, TypedDict, cast
import math
import logging
from app.models.story import (
    AdventureState,
    ChapterType,
    StoryResponse,
    LessonResponse,
    ChapterData,
)
from app.services.llm.prompt_templates import (
    CHOICE_FORMAT_INSTRUCTIONS,
    REASON_CHOICE_FORMAT,
    REFLECTIVE_TECHNIQUES,
    BASE_PHASE_GUIDANCE,
    PLOT_TWIST_GUIDANCE,
    LESSON_CHAPTER_INSTRUCTIONS,
    STORY_CHAPTER_INSTRUCTIONS,
    CONCLUSION_CHAPTER_INSTRUCTIONS,
    CORRECT_ANSWER_CONSEQUENCES,
    INCORRECT_ANSWER_CONSEQUENCES,
    SYSTEM_PROMPT_TEMPLATE,
    REASON_CHALLENGE_TEMPLATES,
    INCORRECT_ANSWER_TEMPLATE,
)


class LessonQuestion(TypedDict):
    """Structure of a lesson question."""

    question: str
    answers: List[Dict[str, Any]]  # List of {text: str, is_correct: bool}
    topic: str
    subtopic: str
    explanation: str


class LessonHistory(TypedDict):
    """Structure of a lesson history entry."""

    question: LessonQuestion
    chosen_answer: str
    is_correct: bool


def _format_lesson_answers(lesson_question: LessonQuestion) -> str:
    """Format the lesson answers section consistently using markdown."""
    # Get the answers in their randomized order
    answers = [answer["text"] for answer in lesson_question["answers"]]
    return f"""- **Option A**: {answers[0]}
- **Option B**: {answers[1]}
- **Option C**: {answers[2]}"""


def _get_phase_guidance(story_phase: str, state: AdventureState) -> str:
    """Get the appropriate guidance based on the Journey Quest story phase.

    Args:
        story_phase: Current phase of the story
        state: Current adventure state containing story elements
    """
    # Get base guidance for the phase
    base_guidance_text = BASE_PHASE_GUIDANCE.get(story_phase, "")

    # Add plot twist guidance for applicable phases
    if story_phase in PLOT_TWIST_GUIDANCE:
        plot_twist_text = PLOT_TWIST_GUIDANCE[story_phase].format(
            plot_twist=state.selected_plot_twist
        )
        return f"{base_guidance_text}\n\n{plot_twist_text}"

    return base_guidance_text


def build_system_prompt(state: AdventureState) -> str:
    """Create a system prompt that establishes the storytelling framework.

    Args:
        state: The current adventure state containing selected story elements
    """
    return SYSTEM_PROMPT_TEMPLATE.format(
        setting_types=state.selected_narrative_elements["setting_types"],
        character_archetypes=state.selected_narrative_elements["character_archetypes"],
        story_rules=state.selected_narrative_elements["story_rules"],
        selected_theme=state.selected_theme,
        selected_moral_teaching=state.selected_moral_teaching,
        visuals=state.selected_sensory_details["visuals"],
        sounds=state.selected_sensory_details["sounds"],
        smells=state.selected_sensory_details["smells"],
    )


def _build_base_prompt(state: AdventureState) -> tuple[str, str, str]:
    """Creates the base prompt with story state information.

    Returns:
        A tuple containing (formatted_story_history, story_phase, chapter_type)
    """
    # Build chapter history with decisions and outcomes
    chapter_history: list[str] = []

    for chapter in state.chapters:  # type: ChapterData
        # Add chapter number with proper formatting
        chapter_history.append(f"## Chapter {chapter.chapter_number}\n")

        # Add the chapter content
        chapter_history.append(f"{chapter.content.strip()}\n")

        # Add lesson outcomes for lesson chapters
        if chapter.chapter_type == ChapterType.LESSON and chapter.response:
            lesson_response = cast(
                LessonResponse, chapter.response
            )  # Type cast since we know it's a LessonResponse
            # Find the correct answer from the answers array
            correct_answer = next(
                answer["text"]
                for answer in lesson_response.question["answers"]
                if answer["is_correct"]
            )
            chapter_history.extend(
                [
                    f"\n**Lesson Question**: {lesson_response.question['question']}\n",
                    f"**Student's Answer**: {lesson_response.chosen_answer}\n",
                    f"**Outcome**: {'Correct' if lesson_response.is_correct else 'Incorrect'}\n",
                    f"**Correct Answer**: {correct_answer}\n",
                ]
            )

        # Add story choices for story chapters
        if chapter.chapter_type == ChapterType.STORY and chapter.response:
            story_response = cast(
                StoryResponse, chapter.response
            )  # Type cast since we know it's a StoryResponse
            chapter_history.append(f"\n**Choice Made**: {story_response.choice_text}\n")

        # Add separator between chapters
        if len(state.chapters) > 1 and chapter != state.chapters[-1]:
            chapter_history.append("---\n")

    # Get story phase from state
    story_phase = state.current_storytelling_phase

    # Get current chapter type
    chapter_type = state.planned_chapter_types[state.current_chapter_number - 1]

    # Format the story history
    formatted_story_history = "".join(
        filter(None, chapter_history)
    )  # filter(None) removes empty strings

    return formatted_story_history, story_phase, chapter_type


def build_reason_chapter_prompt(
    is_correct: bool,
    lesson_question: Dict[str, Any],
    chosen_answer: str,
    base_prompt: str,
    state: Optional[AdventureState] = None,
) -> str:
    """Generate a prompt for chapters that test deeper understanding after a lesson.

    Args:
        is_correct: Whether the previous lesson answer was correct
        lesson_question: The question from the previous lesson
        chosen_answer: The answer chosen in the previous lesson
        base_prompt: Base story state and history
        state: Optional AdventureState for tracking metadata

    Returns:
        A prompt string for generating a chapter that tests deeper understanding
    """
    # Find the correct answer
    correct_answer = next(
        answer["text"] for answer in lesson_question["answers"] if answer["is_correct"]
    )

    # Find incorrect answers
    incorrect_answers = [
        answer["text"]
        for answer in lesson_question["answers"]
        if not answer["is_correct"]
    ]

    if is_correct:
        # For correct answers: Select from multiple challenge types
        import random
        from datetime import datetime

        challenge_type = random.choice(
            [
                "confidence_test",  # Current approach - challenge them to stick with answer
                "application",  # Apply concept to new scenario with same answer
                "connection_making",  # Connect concept to broader theme/moral teaching
                "teaching_moment",  # Character explains concept to another character
            ]
        )

        # Track challenge type in metadata if state is provided
        if state:
            logger = logging.getLogger("story_app")
            logger.debug(f"Selected REASON challenge type: {challenge_type}")

            # Create structured history of challenge types
            if "reason_challenge_history" not in state.metadata:
                state.metadata["reason_challenge_history"] = []

            state.metadata["reason_challenge_history"].append(
                {
                    "chapter": state.current_chapter_number,
                    "challenge_type": challenge_type,
                    "is_correct": is_correct,
                    "timestamp": datetime.now().isoformat(),
                }
            )

            # Also store the most recent challenge type for easy access
            state.metadata["last_reason_challenge_type"] = challenge_type

        # Use the appropriate template based on challenge type
        return f"""{base_prompt}

{
            REASON_CHALLENGE_TEMPLATES[challenge_type].format(
                chosen_answer=chosen_answer,
                question=lesson_question["question"],
                reflective_techniques=REFLECTIVE_TECHNIQUES,
                incorrect_answers=", ".join(incorrect_answers),
                reason_choice_format=REASON_CHOICE_FORMAT,
            )
        }"""
    else:
        # For incorrect answers: Learning opportunity with structured reflection
        return f"""{base_prompt}

{
            INCORRECT_ANSWER_TEMPLATE.format(
                chosen_answer=chosen_answer,
                question=lesson_question["question"],
                correct_answer=correct_answer,
                reflective_techniques=REFLECTIVE_TECHNIQUES,
                reason_choice_format=REASON_CHOICE_FORMAT,
            )
        }"""


def _build_chapter_prompt(
    base_prompt: str,
    story_phase: str,
    chapter_type: ChapterType,
    state: AdventureState,
    lesson_question: Optional[LessonQuestion] = None,
    consequences_guidance: str = "",
    num_previous_lessons: int = 0,
    previous_lessons: Optional[List[LessonResponse]] = None,
) -> str:
    """Builds the appropriate prompt based on chapter type and state.

    Args:
        base_prompt: Base story state and history
        story_phase: Current phase of the story (Exposition, Rising, Trials, Climax, Return)
        chapter_type: Type of chapter to generate (LESSON, STORY, REASON, or CONCLUSION)
        lesson_question: Question data for lesson chapters
        consequences_guidance: Guidance based on previous lesson outcomes
        num_previous_lessons: Number of previous lesson chapters
        previous_lessons: History of previous lesson responses
    """
    # Handle REASON chapters
    if chapter_type == ChapterType.REASON:
        # A REASON chapter must follow a LESSON chapter
        if not previous_lessons or len(previous_lessons) == 0:
            raise ValueError("REASON chapter requires a previous LESSON")

        last_lesson = previous_lessons[-1]
        return build_reason_chapter_prompt(
            is_correct=last_lesson.is_correct,
            lesson_question=last_lesson.question,
            chosen_answer=last_lesson.chosen_answer,
            base_prompt=base_prompt,
            state=state,
        )

    # Handle lesson chapters
    elif chapter_type == ChapterType.LESSON:
        continuation_text = ""
        if num_previous_lessons > 0:
            continuation_text = f"""Continue the story, acknowledging the previous lesson{" and earlier lessons" if num_previous_lessons > 1 else ""} while leading to a new question.

{consequences_guidance}

"""
            if previous_lessons:
                continuation_text += f"Previous lesson history:\n{format_lesson_history(previous_lessons)}\n\n"

        return f"""{base_prompt}

{continuation_text}{_get_phase_guidance(story_phase, state)}

Continue the story naturally, weaving in a situation or moment that raises this core question:
{lesson_question["question"]}

CRITICAL INSTRUCTIONS:
1. {"Build on the consequences of the previous lesson, showing how it connects to this new challenge" if num_previous_lessons > 0 else "Let the story flow organically towards this new challenge"}
{LESSON_CHAPTER_INSTRUCTIONS}

{_format_lesson_answers(lesson_question)}"""

    # Handle story chapters
    elif chapter_type == ChapterType.STORY:
        continuation_text = ""
        if num_previous_lessons > 0:
            continuation_text = f"""Continue the story based on the character's previous lesson{" and earlier lessons" if num_previous_lessons > 1 else ""}.

{consequences_guidance}

"""
            if previous_lessons:
                continuation_text += f"Previous lesson history:\n{format_lesson_history(previous_lessons)}\n\n"

        return f"""{base_prompt}

{continuation_text}{_get_phase_guidance(story_phase, state)}

{STORY_CHAPTER_INSTRUCTIONS}

IMPORTANT:
1. {"The story should clearly but naturally acknowledge the impact of their previous lesson" if num_previous_lessons > 0 else "DO NOT include any lesson questions"}
2. Build towards a natural story decision point
3. The story choices will be provided separately - do not list them in the narrative
4. End the scene at a moment of decision

{CHOICE_FORMAT_INSTRUCTIONS}"""

    # Handle conclusion chapters
    else:  # chapter_type == ChapterType.CONCLUSION
        continuation_text = ""
        if num_previous_lessons > 0:
            continuation_text = f"""Continue the story, incorporating the wisdom gained from the previous lesson{" and earlier lessons" if num_previous_lessons > 1 else ""}.

{consequences_guidance}

"""
            if previous_lessons:
                continuation_text += f"Previous lesson history:\n{format_lesson_history(previous_lessons)}\n\n"

        return f"""{base_prompt}

{continuation_text}{_get_phase_guidance(story_phase, state)}

{CONCLUSION_CHAPTER_INSTRUCTIONS}

IMPORTANT:
1. This is the final chapter - provide a complete and satisfying resolution
2. {"Demonstrate how the lessons learned have contributed to the character's growth" if num_previous_lessons > 0 else "Focus on the character's personal growth through their journey"}
3. DO NOT include any choices or decision points
4. End with a sense of closure while highlighting the character's transformation"""


def build_user_prompt(
    state: AdventureState,
    lesson_question: Optional[LessonQuestion] = None,
    previous_lessons: Optional[List[LessonResponse]] = None,
) -> str:
    """Create a user prompt that includes story state and current requirements."""
    from app.services.llm.prompt_templates import USER_PROMPT_TEMPLATE

    # Get base prompt components
    story_history, story_phase, current_chapter_type = _build_base_prompt(state)

    # Debug logging for previous lessons
    logger = logging.getLogger("story_app")
    logger.debug("\n=== DEBUG: Previous Lessons in build_user_prompt ===")
    if previous_lessons:
        logger.debug(f"Number of previous lessons: {len(previous_lessons)}")
        for i, lesson in enumerate(previous_lessons, 1):
            logger.debug(f"Lesson {i}:")
            logger.debug(f"Question: {lesson.question['question']}")
            logger.debug(f"Chosen Answer: {lesson.chosen_answer}")
            logger.debug(f"Is Correct: {lesson.is_correct}")
    else:
        logger.debug("No previous lessons provided")
    logger.debug("===============================================\n")

    # Handle consequences for lesson responses
    consequences_guidance = ""
    num_previous_lessons = 0
    if previous_lessons:
        num_previous_lessons = len(previous_lessons)
        if num_previous_lessons > 0:
            last_lesson = previous_lessons[-1]
            logger.debug("\n=== DEBUG: Processing Consequences ===")
            logger.debug(f"Last lesson correct: {last_lesson.is_correct}")
            logger.debug(f"Last lesson question: {last_lesson.question}")
            logger.debug(f"Last lesson chosen answer: {last_lesson.chosen_answer}")
            consequences_guidance = process_consequences(
                last_lesson.is_correct,
                last_lesson.question,
                last_lesson.chosen_answer,
                state.current_chapter_number,
            )
            logger.debug(f"Generated consequences: {consequences_guidance}")
            logger.debug("===================================\n")

    # Determine chapter type and get appropriate instructions
    chapter_type = ChapterType.LESSON if lesson_question else current_chapter_type

    # Get phase guidance
    phase_guidance = _get_phase_guidance(story_phase, state)

    # Get chapter-specific instructions
    if chapter_type == ChapterType.LESSON and lesson_question:
        # For lesson chapters
        continuation_text = ""
        if num_previous_lessons > 0:
            continuation_text = f"""## Previous Lesson Impact
{consequences_guidance}

"""
            if previous_lessons:
                continuation_text += (
                    f"### Lesson History\n{format_lesson_history(previous_lessons)}\n\n"
                )

        chapter_instructions = f"""{LESSON_CHAPTER_INSTRUCTIONS}

## Core Question
{lesson_question["question"]}

### Available Answers
{_format_lesson_answers(lesson_question)}

{continuation_text}"""

    elif (
        chapter_type == ChapterType.REASON
        and previous_lessons
        and len(previous_lessons) > 0
    ):
        # For reason chapters
        last_lesson = previous_lessons[-1]
        # Use the existing build_reason_chapter_prompt but extract just the instructions part
        reason_prompt = build_reason_chapter_prompt(
            is_correct=last_lesson.is_correct,
            lesson_question=last_lesson.question,
            chosen_answer=last_lesson.chosen_answer,
            base_prompt="",  # Empty base prompt since we're just extracting instructions
            state=state,
        )
        # Remove the empty base prompt part if it exists
        chapter_instructions = reason_prompt.strip()

    elif chapter_type == ChapterType.STORY:
        # For story chapters
        continuation_text = ""
        if num_previous_lessons > 0:
            continuation_text = f"""## Previous Lesson Impact
{consequences_guidance}

"""
            if previous_lessons:
                continuation_text += (
                    f"### Lesson History\n{format_lesson_history(previous_lessons)}\n\n"
                )

        chapter_instructions = f"""{STORY_CHAPTER_INSTRUCTIONS}

{continuation_text}

{CHOICE_FORMAT_INSTRUCTIONS}"""

    else:  # chapter_type == ChapterType.CONCLUSION
        # For conclusion chapters
        continuation_text = ""
        if num_previous_lessons > 0:
            continuation_text = f"""## Previous Lesson Impact
{consequences_guidance}

"""
            if previous_lessons:
                continuation_text += (
                    f"### Lesson History\n{format_lesson_history(previous_lessons)}\n\n"
                )

        chapter_instructions = f"""{CONCLUSION_CHAPTER_INSTRUCTIONS}

{continuation_text}"""

    # Create additional guidance with proper formatting
    additional_guidance = ""
    if num_previous_lessons > 0:
        guidance_points = ["Build on the consequences of the previous lesson"]
        if num_previous_lessons > 1:
            guidance_points.append(
                "Show how previous lessons have impacted the character"
            )

        formatted_points = "\n".join(
            [f"{i + 1}. {point}" for i, point in enumerate(guidance_points)]
        )
        additional_guidance = f"## Continuity Guidance\n{formatted_points}"

    # Format the final prompt using the template
    return USER_PROMPT_TEMPLATE.format(
        chapter_number=state.current_chapter_number,
        story_length=state.story_length,
        chapter_type=chapter_type,
        story_phase=story_phase,
        correct_lessons=state.correct_lesson_answers,
        total_lessons=state.total_lessons,
        story_history=story_history,
        phase_guidance=phase_guidance,
        chapter_instructions=chapter_instructions,
        additional_guidance=additional_guidance,
    )


def format_lesson_history(previous_lessons: List[LessonResponse]) -> str:
    """Format the lesson history for inclusion in the prompt using markdown."""
    history = []
    for i, lesson in enumerate(previous_lessons, 1):
        history.append(f"#### Lesson {i}: {lesson.question['question']}")
        history.append(
            f"- **Chosen Answer**: {lesson.chosen_answer} ({'✓ Correct' if lesson.is_correct else '✗ Incorrect'})"
        )
        if not lesson.is_correct:
            # Find the correct answer from the answers array
            correct_answer = next(
                answer["text"]
                for answer in lesson.question["answers"]
                if answer["is_correct"]
            )
            history.append(f"- **Correct Answer**: {correct_answer}")
        history.append("")  # Add blank line between lessons
    return "\n".join(history)


def process_consequences(
    is_correct: bool,
    lesson_question: Dict[str, Any],
    chosen_answer: str,
    chapter_number: int,  # Kept for backward compatibility but no longer used
) -> str:
    """Generate appropriate story consequences based on lesson response."""
    # Find the correct answer from the answers array
    correct_answer = next(
        answer["text"] for answer in lesson_question["answers"] if answer["is_correct"]
    )

    if is_correct:
        return CORRECT_ANSWER_CONSEQUENCES.format(
            correct_answer=correct_answer, question=lesson_question["question"]
        )
    else:
        return INCORRECT_ANSWER_CONSEQUENCES.format(
            chosen_answer=chosen_answer,
            correct_answer=correct_answer,
            question=lesson_question["question"],
        )
