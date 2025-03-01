"""
Streamlined prompt engineering functions for Learning Odyssey.

This module provides streamlined alternatives to the prompt engineering functions
in prompt_engineering.py, with a focus on reducing redundancy and improving clarity
by consolidating critical rules and agency instructions.
"""

import logging
from typing import Optional, Dict, Any, List, cast
from app.models.story import AdventureState, ChapterType, StoryResponse, LessonResponse
from app.services.llm.prompt_engineering import (
    LessonQuestion,
    _build_base_prompt,
    _get_phase_guidance,
    process_consequences,
    format_lesson_history,
)
from app.services.llm.streamlined_prompt_templates import (
    STREAMLINED_SYSTEM_PROMPT,
    STREAMLINED_FIRST_CHAPTER_PROMPT,
    get_streamlined_agency_category,
)


def build_streamlined_system_prompt(state: AdventureState) -> str:
    """Create a streamlined system prompt that establishes the storytelling framework.

    Args:
        state: The current adventure state containing selected story elements
    """
    return STREAMLINED_SYSTEM_PROMPT.format(
        setting_types=state.selected_narrative_elements["setting_types"],
        character_archetypes=state.selected_narrative_elements["character_archetypes"],
        story_rules=state.selected_narrative_elements["story_rules"],
        selected_theme=state.selected_theme,
        selected_moral_teaching=state.selected_moral_teaching,
        visuals=state.selected_sensory_details["visuals"],
        sounds=state.selected_sensory_details["sounds"],
        smells=state.selected_sensory_details["smells"],
    )


def build_streamlined_first_chapter_prompt(state: AdventureState) -> str:
    """Create a streamlined prompt for the first chapter with consolidated rules and agency instructions.

    Args:
        state: The current adventure state
    """
    # Get base prompt components
    story_history, story_phase, _ = _build_base_prompt(state)

    # Get phase guidance
    phase_guidance = _get_phase_guidance(story_phase, state)

    # Get random agency category
    agency_category_name, agency_options = get_streamlined_agency_category()

    # Log agency category selection
    logger = logging.getLogger("story_app")
    logger.debug(f"First chapter: Using agency category: {agency_category_name}")

    return STREAMLINED_FIRST_CHAPTER_PROMPT.format(
        chapter_number=state.current_chapter_number,
        story_length=state.story_length,
        chapter_type=ChapterType.STORY,
        story_phase=story_phase,
        correct_lessons=state.correct_lesson_answers,
        total_lessons=state.total_lessons,
        story_history=story_history,
        phase_guidance=phase_guidance,
        agency_category_name=agency_category_name,
        agency_options=agency_options,
    )


def build_streamlined_prompt(
    state: AdventureState,
    lesson_question: Optional[LessonQuestion] = None,
    previous_lessons: Optional[List[LessonResponse]] = None,
) -> tuple[str, str]:
    """Create streamlined system and user prompts for the LLM.

    This function handles special cases like the first chapter with consolidated
    rules and agency instructions.

    Args:
        state: The current adventure state
        lesson_question: Optional question data for lesson chapters
        previous_lessons: Optional history of previous lesson responses

    Returns:
        A tuple containing (system_prompt, user_prompt)
    """
    # Build the streamlined system prompt
    system_prompt = build_streamlined_system_prompt(state)

    # For the first chapter, use the streamlined first chapter prompt
    if (
        state.current_chapter_number == 1
        and state.planned_chapter_types[0] == ChapterType.STORY
    ):
        user_prompt = build_streamlined_first_chapter_prompt(state)
    else:
        # For other chapters, use the existing prompt engineering functions
        # This could be extended in the future to streamline other chapter types
        from app.services.llm.prompt_engineering import build_user_prompt

        user_prompt = build_user_prompt(state, lesson_question, previous_lessons)

    return system_prompt, user_prompt
