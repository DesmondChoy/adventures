"""
Prompt engineering functions for Learning Odyssey.

This module provides functions for generating prompts for the Learning Odyssey
storytelling system. It uses templates from prompt_templates.py to construct
complete prompts for different chapter types and scenarios.
"""

from typing import Any, Dict, Optional, List, TypedDict, cast, Tuple
import logging
import re
from datetime import datetime
from app.models.story import (
    AdventureState,
    ChapterType,
    StoryResponse,
    LessonResponse,
)
from app.services.llm.prompt_templates import (
    SYSTEM_PROMPT_TEMPLATE,
    FIRST_CHAPTER_PROMPT,
    STORY_CHAPTER_PROMPT,
    LESSON_CHAPTER_PROMPT,
    REFLECT_CHAPTER_PROMPT,
    CONCLUSION_CHAPTER_PROMPT,
    REFLECT_CHOICE_FORMAT,
    BASE_PHASE_GUIDANCE,
    PLOT_TWIST_GUIDANCE,
    CORRECT_ANSWER_CONSEQUENCES,
    INCORRECT_ANSWER_CONSEQUENCES,
    AGENCY_GUIDANCE,
    REFLECT_CONFIG,
    get_choice_instructions,
    get_agency_category,
    get_reflective_technique,
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
    """Get the base phase guidance for the current story phase.

    This function returns only the base guidance without plot twist guidance,
    as plot twist guidance is handled separately in story chapter prompts.

    Args:
        story_phase: Current phase of the story
        state: Current adventure state containing story elements
    """
    # Get base guidance for the phase
    base_guidance_text = BASE_PHASE_GUIDANCE.get(story_phase, "")

    # If it's the Exposition phase, replace the adventure_topic placeholder
    if story_phase == "Exposition" and "non_random_elements" in state.metadata:
        adventure_topic = state.metadata["non_random_elements"].get("name", "")
        base_guidance_text = base_guidance_text.replace(
            "{adventure_topic}", adventure_topic
        )

    return base_guidance_text


def build_system_prompt(state: AdventureState) -> str:
    """Create a system prompt that establishes the storytelling framework.

    Args:
        state: The current adventure state containing selected story elements
    """
    return SYSTEM_PROMPT_TEMPLATE.format(
        settings=state.selected_narrative_elements["settings"],
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

    # Get the explanation from the lesson question, or use a default if not available
    explanation = lesson_question.get("explanation", "")

    if is_correct:
        return CORRECT_ANSWER_CONSEQUENCES.format(
            correct_answer=correct_answer,
            question=lesson_question["question"],
            explanation=explanation,
        )
    else:
        return INCORRECT_ANSWER_CONSEQUENCES.format(
            chosen_answer=chosen_answer,
            correct_answer=correct_answer,
            question=lesson_question["question"],
            explanation=explanation,
        )


def build_first_chapter_prompt(state: AdventureState) -> str:
    """Build a prompt for the first chapter (STORY type).

    Args:
        state: The current adventure state
    """
    # Get base prompt components
    story_history, story_phase, _ = _build_base_prompt(state)

    # Get random agency category, 3 formatted options, and extracted option names
    agency_category_name, agency_options, option_names = get_agency_category()

    # Clean options by removing visual details in brackets directly
    cleaned_agency_options = re.sub(r"\s*\[.*?\]\s*", " ", agency_options)

    # Log agency category selection
    logger = logging.getLogger("story_app")
    logger.debug(f"First chapter: Using agency category: {agency_category_name}")
    logger.debug(f"Selected options: {', '.join(option_names)}")

    return FIRST_CHAPTER_PROMPT.format(
        chapter_number=state.current_chapter_number,
        story_length=state.story_length,
        chapter_type=ChapterType.STORY,
        story_phase=story_phase,
        correct_lessons=state.correct_lesson_answers,
        total_lessons=state.total_lessons,
        story_history=story_history,
        agency_category_name=agency_category_name,
        agency_options=cleaned_agency_options,
        option_a=option_names[0],
        option_b=option_names[1],
        option_c=option_names[2],
    )


def build_story_chapter_prompt(
    state: AdventureState,
    previous_lessons: Optional[List[LessonResponse]] = None,
) -> str:
    """Build a prompt for STORY chapters (except the first chapter).

    Args:
        state: The current adventure state
        previous_lessons: Optional history of previous lesson responses
    """
    # Get base prompt components
    story_history, story_phase, _ = _build_base_prompt(state)

    # Get consequences guidance if there are previous lessons
    if previous_lessons and len(previous_lessons) > 0:
        last_lesson = previous_lessons[-1]
        consequences_guidance = process_consequences(
            last_lesson.is_correct,
            last_lesson.question,
            last_lesson.chosen_answer,
            state.current_chapter_number,
        )
    else:
        consequences_guidance = "Continue the narrative journey"

    # Format lesson history if available
    lesson_history = ""
    if previous_lessons and len(previous_lessons) > 0:
        lesson_history = (
            f"## Previous Learning\n{format_lesson_history(previous_lessons)}"
        )

    # Get agency guidance if available
    agency_guidance = ""
    if "agency" in state.metadata:
        agency = state.metadata["agency"]

        # Special handling for climax phase
        if story_phase == "Climax":
            agency_type = agency.get("type", "choice")
            agency_name = agency.get("name", "from Chapter 1")

            agency_guidance = AGENCY_GUIDANCE["climax"].format(
                agency_type=agency_type, agency_name=agency_name
            )

            logger = logging.getLogger("story_app")
            logger.debug(
                f"Climax phase: Incorporating agency: {agency_type}/{agency_name}"
            )
        else:
            agency_guidance = f"""
## Agency Presence
Incorporate the character's {agency.get("type", "choice")} ({agency.get("name", "from Chapter 1")}) in a way that feels natural to this part of the story.
It should be present and meaningful without following a predictable pattern.
"""

    # Get plot twist guidance if applicable
    plot_twist_guidance = ""
    if story_phase in PLOT_TWIST_GUIDANCE:
        plot_twist_guidance = PLOT_TWIST_GUIDANCE[story_phase].format(
            plot_twist=state.selected_plot_twist
        )

    # Get choice instructions based on story phase
    choice_format = get_choice_instructions(story_phase)

    return STORY_CHAPTER_PROMPT.format(
        chapter_number=state.current_chapter_number,
        story_length=state.story_length,
        chapter_type=ChapterType.STORY,
        story_phase=story_phase,
        correct_lessons=state.correct_lesson_answers,
        total_lessons=state.total_lessons,
        story_history=story_history,
        consequences_guidance=consequences_guidance,
        lesson_history=lesson_history,
        agency_guidance=agency_guidance,
        plot_twist_guidance=plot_twist_guidance,
    )


def build_lesson_chapter_prompt(
    state: AdventureState,
    lesson_question: LessonQuestion,
    previous_lessons: Optional[List[LessonResponse]] = None,
) -> str:
    """Build a prompt for LESSON chapters.

    Args:
        state: The current adventure state
        lesson_question: The question data for this lesson
        previous_lessons: Optional history of previous lesson responses
    """
    # Get base prompt components
    story_history, story_phase, _ = _build_base_prompt(state)

    # Format lesson answers
    formatted_answers = _format_lesson_answers(lesson_question)

    # Get consequences guidance if there are previous lessons
    if previous_lessons and len(previous_lessons) > 0:
        last_lesson = previous_lessons[-1]
        consequences_guidance = process_consequences(
            last_lesson.is_correct,
            last_lesson.question,
            last_lesson.chosen_answer,
            state.current_chapter_number,
        )
    else:
        consequences_guidance = "Introduce a new learning opportunity"

    # Format lesson history if available
    lesson_history = ""
    if previous_lessons and len(previous_lessons) > 0:
        lesson_history = (
            f"## Previous Learning\n{format_lesson_history(previous_lessons)}"
        )

    # Get agency guidance if available
    agency_guidance = ""
    if "agency" in state.metadata:
        agency = state.metadata["agency"]
        agency_guidance = f"""
## Agency Connection
The character's {agency.get("type", "choice")} ({agency.get("name", "from Chapter 1")}) should be present in this chapter, potentially:
- Creating a situation that leads to the lesson question
- Helping frame the educational content in a narrative context
- Being affected by or connected to the knowledge being tested
"""

    return LESSON_CHAPTER_PROMPT.format(
        chapter_number=state.current_chapter_number,
        story_length=state.story_length,
        chapter_type=ChapterType.LESSON,
        story_phase=story_phase,
        correct_lessons=state.correct_lesson_answers,
        total_lessons=state.total_lessons,
        story_history=story_history,
        consequences_guidance=consequences_guidance,
        lesson_history=lesson_history,
        agency_guidance=agency_guidance,
        question=lesson_question["question"],
        formatted_answers=formatted_answers,
        topic=lesson_question["topic"],
    )


def build_reflect_chapter_prompt(
    state: AdventureState,
    previous_lesson: LessonResponse,
) -> str:
    """Build a prompt for REFLECT chapters.

    Args:
        state: The current adventure state
        previous_lesson: The previous lesson response to reflect on
    """
    # Get base prompt components
    story_history, story_phase, _ = _build_base_prompt(state)

    # Get reflective technique
    reflective_technique = get_reflective_technique()

    # Determine if the answer was correct
    is_correct = previous_lesson.is_correct

    # Get the correct answer
    correct_answer = next(
        answer["text"]
        for answer in previous_lesson.question["answers"]
        if answer["is_correct"]
    )

    # Get the explanation from the question data and create explanation guidance
    explanation = previous_lesson.question.get("explanation", "")
    explanation_guidance = (
        f'Use this explanation to guide reflection: "{explanation}"'
        if explanation
        else "Help the character understand the concept through thoughtful reflection."
    )

    # Select the appropriate configuration
    config = REFLECT_CONFIG["correct"] if is_correct else REFLECT_CONFIG["incorrect"]

    # Format the exploration_goal with the actual question
    formatted_exploration_goal = config["exploration_goal"].format(
        question=previous_lesson.question["question"]
    )

    # Get agency guidance if available
    agency_guidance = ""
    if "agency" in state.metadata:
        agency = state.metadata["agency"]
        agency_type = agency.get("type", "choice")
        agency_name = agency.get("name", "from Chapter 1")

        # Get the appropriate agency guidance
        agency_guidance = AGENCY_GUIDANCE[
            "correct" if is_correct else "incorrect"
        ].format(agency_type=agency_type, agency_name=agency_name)

        # Log agency guidance selection
        logger = logging.getLogger("story_app")
        logger.debug(
            f"Using agency guidance for {'correct' if is_correct else 'incorrect'} answer"
        )

        # Track agency evolution in metadata
        if "agency_evolution" not in state.metadata:
            state.metadata["agency_evolution"] = []

        state.metadata["agency_evolution"].append(
            {
                "chapter": state.current_chapter_number,
                "chapter_type": "REFLECT",
                "is_correct": is_correct,
                "timestamp": datetime.now().isoformat(),
            }
        )

    # Track reflection in metadata
    if "reflect_challenge_history" not in state.metadata:
        state.metadata["reflect_challenge_history"] = []

    state.metadata["reflect_challenge_history"].append(
        {
            "chapter": state.current_chapter_number,
            "is_correct": is_correct,
            "timestamp": datetime.now().isoformat(),
            "approach": "narrative_driven",
        }
    )

    # Also store the most recent reflection type for easy access
    state.metadata["last_reflect_approach"] = "narrative_driven"

    logger = logging.getLogger("story_app")
    logger.debug(
        f"Using narrative-driven REFLECT approach for {'correct' if is_correct else 'incorrect'} answer"
    )

    return REFLECT_CHAPTER_PROMPT.format(
        chapter_number=state.current_chapter_number,
        story_length=state.story_length,
        chapter_type=ChapterType.REFLECT,
        story_phase=story_phase,
        correct_lessons=state.correct_lesson_answers,
        total_lessons=state.total_lessons,
        story_history=story_history,
        question=previous_lesson.question["question"],
        chosen_answer=previous_lesson.chosen_answer,
        answer_status=config["answer_status"],
        correct_answer_info=config["correct_answer_info"].format(
            correct_answer=correct_answer
        )
        if not is_correct
        else config["correct_answer_info"],
        explanation_guidance=explanation_guidance,
        reflective_technique=reflective_technique,
        acknowledgment_guidance=config["acknowledgment_guidance"],
        exploration_goal=formatted_exploration_goal,
        theme=state.selected_theme,
        agency_guidance=agency_guidance,
        reflect_choice_format=REFLECT_CHOICE_FORMAT,
    )


def build_conclusion_chapter_prompt(
    state: AdventureState,
    previous_lessons: Optional[List[LessonResponse]] = None,
) -> str:
    """Build a prompt for CONCLUSION chapters.

    Args:
        state: The current adventure state
        previous_lessons: Optional history of previous lesson responses
    """
    # Get base prompt components
    story_history, story_phase, _ = _build_base_prompt(state)

    # Get consequences guidance if there are previous lessons
    consequences_guidance = ""
    if previous_lessons and len(previous_lessons) > 0:
        last_lesson = previous_lessons[-1]
        consequences_guidance = process_consequences(
            last_lesson.is_correct,
            last_lesson.question,
            last_lesson.chosen_answer,
            state.current_chapter_number,
        )

    # Format lesson history if available
    lesson_history = ""
    if previous_lessons and len(previous_lessons) > 0:
        lesson_history = (
            f"## Learning Journey\n{format_lesson_history(previous_lessons)}"
        )

    # Get agency guidance if available
    agency_resolution_guidance = (
        "Provide a satisfying resolution to the character's journey"
    )
    if "agency" in state.metadata:
        agency = state.metadata["agency"]
        agency_type = agency.get("type", "choice")
        agency_name = agency.get("name", "from Chapter 1")

        agency_resolution_guidance = AGENCY_GUIDANCE["conclusion"].format(
            agency_type=agency_type, agency_name=agency_name
        )

    return CONCLUSION_CHAPTER_PROMPT.format(
        chapter_number=state.current_chapter_number,
        story_length=state.story_length,
        chapter_type=ChapterType.CONCLUSION,
        story_phase=story_phase,
        correct_lessons=state.correct_lesson_answers,
        total_lessons=state.total_lessons,
        story_history=story_history,
        lesson_history=lesson_history,
        agency_resolution_guidance=agency_resolution_guidance,
    )


def build_user_prompt(
    state: AdventureState,
    lesson_question: Optional[LessonQuestion] = None,
    previous_lessons: Optional[List[LessonResponse]] = None,
) -> str:
    """Create a user prompt that includes story state and current requirements.

    Args:
        state: The current adventure state
        lesson_question: Optional question data for lesson chapters
        previous_lessons: Optional history of previous lesson responses
    """
    # Determine chapter type
    chapter_type = state.planned_chapter_types[state.current_chapter_number - 1]

    # Get story phase
    story_phase = state.current_storytelling_phase

    # Get phase guidance
    phase_guidance = _get_phase_guidance(story_phase, state)

    # Build the appropriate user prompt based on chapter type
    prompt = ""
    if chapter_type == ChapterType.STORY:
        if state.current_chapter_number == 1:
            # For the first chapter, use the first chapter prompt
            prompt = build_first_chapter_prompt(state)
        else:
            # For other story chapters, use the story chapter prompt
            prompt = build_story_chapter_prompt(state, previous_lessons)
    elif chapter_type == ChapterType.LESSON and lesson_question:
        # For lesson chapters, use the lesson chapter prompt
        prompt = build_lesson_chapter_prompt(state, lesson_question, previous_lessons)
    elif (
        chapter_type == ChapterType.REFLECT
        and previous_lessons
        and len(previous_lessons) > 0
    ):
        # For reflect chapters, use the reflect chapter prompt
        prompt = build_reflect_chapter_prompt(state, previous_lessons[-1])
    elif chapter_type == ChapterType.CONCLUSION:
        # For conclusion chapters, use the conclusion chapter prompt
        prompt = build_conclusion_chapter_prompt(state, previous_lessons)
    else:
        # This should never happen, but just in case
        logger = logging.getLogger("story_app")
        logger.error(f"Unsupported chapter type: {chapter_type}")
        raise ValueError(f"Unsupported chapter type: {chapter_type}")

    # Add phase guidance to the prompt if available
    if phase_guidance:
        prompt = f"{phase_guidance}\n\n{prompt}"

    return prompt


def build_summary_chapter_prompt(state: AdventureState) -> Tuple[str, str]:
    """Create system and user prompts for generating a summary of the adventure.

    This function builds prompts specifically for the SUMMARY chapter type,
    which recaps the entire adventure and highlights the educational content.

    Args:
        state: The current adventure state containing all chapters and responses

    Returns:
        A tuple containing (system_prompt, user_prompt)
    """
    # Create a system prompt for the summary
    system_prompt = """You are creating a visually engaging summary page for an educational adventure story. 
This summary should recap the entire journey and highlight the educational content in a way that's engaging for children aged 6-12.
The summary should have two main sections:
1. A narrative journey recap that highlights key moments from each chapter
2. A learning report that shows all questions, answers, and whether they were answered correctly

Format your response with clear section headings and use engaging, child-friendly language.
Do not include any choices or interactive elements in your response."""

    # Create a user prompt with details about the adventure
    user_prompt = f"""Create a summary page for an educational adventure in {state.metadata["non_random_elements"]["name"]}.

Adventure Details:
- Theme: {state.selected_theme}
- Moral Teaching: {state.selected_moral_teaching}
- Setting: {state.selected_narrative_elements.get("settings", "Unknown")}
- Agency Choice: {state.metadata.get("agency", {}).get("description", "Unknown")}

Chapter Recap:
"""

    # Add chapter content summaries
    for chapter in state.chapters:
        # Get a short excerpt from each chapter (first 100 characters)
        excerpt = (
            chapter.content[:100] + "..."
            if len(chapter.content) > 100
            else chapter.content
        )
        user_prompt += f"- Chapter {chapter.chapter_number} ({chapter.chapter_type.value}): {excerpt}\n"

    # Add learning questions and responses
    user_prompt += "\nLearning Questions and Responses:\n"
    for chapter in state.chapters:
        if chapter.chapter_type == ChapterType.LESSON and chapter.response:
            question = chapter.response.question["question"]
            chosen_answer = chapter.response.chosen_answer
            is_correct = chapter.response.is_correct
            correct_answer = next(
                answer["text"]
                for answer in chapter.response.question["answers"]
                if answer["is_correct"]
            )
            explanation = chapter.response.question.get("explanation", "")

            user_prompt += f"- Question: {question}\n"
            user_prompt += f"  - Chosen Answer: {chosen_answer}\n"
            user_prompt += f"  - Correct Answer: {correct_answer}\n"
            user_prompt += f"  - Result: {'Correct' if is_correct else 'Incorrect'}\n"
            if explanation:
                user_prompt += f"  - Explanation: {explanation}\n"
            user_prompt += "\n"

    return system_prompt, user_prompt


def build_prompt(
    state: AdventureState,
    lesson_question: Optional[LessonQuestion] = None,
    previous_lessons: Optional[List[LessonResponse]] = None,
    context: Optional[Dict[str, Any]] = None,
) -> Tuple[str, str]:
    """Create system and user prompts for the LLM.

    This function handles all chapter types with the optimized approach.

    Args:
        state: The current adventure state
        lesson_question: Optional question data for lesson chapters
        previous_lessons: Optional history of previous lesson responses
        context: Optional context with additional parameters

    Returns:
        A tuple containing (system_prompt, user_prompt)
    """
    # Check if we have a prompt override in the context
    if context and "prompt_override" in context:
        # Use a simple system prompt for direct text generation
        system_prompt = (
            "You are a helpful assistant that follows instructions precisely."
        )
        user_prompt = context["prompt_override"]
        return system_prompt, user_prompt

    # Build the system prompt
    system_prompt = build_system_prompt(state)

    # Build the user prompt
    user_prompt = build_user_prompt(state, lesson_question, previous_lessons)

    return system_prompt, user_prompt
