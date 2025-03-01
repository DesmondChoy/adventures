"""
Further streamlined prompt engineering functions for Learning Odyssey.

This module provides even more streamlined alternatives to the prompt engineering
functions, with additional optimizations to reduce redundancy and improve clarity
beyond the initial streamlining.
"""

import logging
from typing import Optional, Dict, Any, List, Tuple, cast
from app.models.story import AdventureState, ChapterType, StoryResponse, LessonResponse
from app.services.llm.prompt_engineering import (
    LessonQuestion,
    _build_base_prompt,
    process_consequences,
    format_lesson_history,
)
from app.services.llm.further_streamlined_prompt_templates import (
    FURTHER_STREAMLINED_SYSTEM_PROMPT,
    FURTHER_STREAMLINED_FIRST_CHAPTER_PROMPT,
    get_further_streamlined_agency_category,
    get_exposition_focus,
)


def build_further_streamlined_system_prompt(state: AdventureState) -> str:
    """Create a further streamlined system prompt that establishes the storytelling framework.

    Args:
        state: The current adventure state containing selected story elements
    """
    return FURTHER_STREAMLINED_SYSTEM_PROMPT.format(
        setting_types=state.selected_narrative_elements["setting_types"],
        character_archetypes=state.selected_narrative_elements["character_archetypes"],
        story_rules=state.selected_narrative_elements["story_rules"],
        selected_theme=state.selected_theme,
        selected_moral_teaching=state.selected_moral_teaching,
        visuals=state.selected_sensory_details["visuals"],
        sounds=state.selected_sensory_details["sounds"],
        smells=state.selected_sensory_details["smells"],
    )


def build_further_streamlined_first_chapter_prompt(state: AdventureState) -> str:
    """Create a further streamlined prompt for the first chapter with consolidated sections.

    Args:
        state: The current adventure state
    """
    # Get base prompt components
    story_history, story_phase, _ = _build_base_prompt(state)

    # Get exposition focus for the current phase
    exposition_focus = get_exposition_focus(story_phase)

    # Get random agency category with more concise formatting
    agency_category_name, agency_options = get_further_streamlined_agency_category()

    # Log agency category selection
    logger = logging.getLogger("story_app")
    logger.debug(f"First chapter: Using agency category: {agency_category_name}")

    return FURTHER_STREAMLINED_FIRST_CHAPTER_PROMPT.format(
        chapter_number=state.current_chapter_number,
        story_length=state.story_length,
        chapter_type=ChapterType.STORY,
        story_phase=story_phase,
        correct_lessons=state.correct_lesson_answers,
        total_lessons=state.total_lessons,
        story_history=story_history,
        exposition_focus=exposition_focus,
        agency_category_name=agency_category_name,
        agency_options=agency_options,
    )


def build_further_streamlined_prompt(
    state: AdventureState,
    lesson_question: Optional[LessonQuestion] = None,
    previous_lessons: Optional[List[LessonResponse]] = None,
) -> Tuple[str, str]:
    """Create further streamlined system and user prompts for the LLM.

    This function handles special cases like the first chapter with consolidated
    sections and reduced redundancy.

    Args:
        state: The current adventure state
        lesson_question: Optional question data for lesson chapters
        previous_lessons: Optional history of previous lesson responses

    Returns:
        A tuple containing (system_prompt, user_prompt)
    """
    # Build the further streamlined system prompt
    system_prompt = build_further_streamlined_system_prompt(state)

    # For the first chapter, use the further streamlined first chapter prompt
    if (
        state.current_chapter_number == 1
        and state.planned_chapter_types[0] == ChapterType.STORY
    ):
        user_prompt = build_further_streamlined_first_chapter_prompt(state)
    else:
        # For other chapters, use the original prompt engineering functions
        # This could be extended in the future to streamline other chapter types
        from app.services.llm.prompt_engineering import build_user_prompt

        user_prompt = build_user_prompt(state, lesson_question, previous_lessons)

    return system_prompt, user_prompt
