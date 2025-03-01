"""
Test script to compare original and streamlined prompts.

This script demonstrates the differences between the original and streamlined
prompt engineering approaches, highlighting the improvements in clarity,
organization, and reduction of redundancy.
"""

import sys
import os
import logging
from typing import Dict, Any

# Add the parent directory to the path so we can import the app modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from app.models.story import AdventureState, ChapterType
from app.services.llm.prompt_engineering import (
    build_system_prompt,
    build_user_prompt,
    _build_chapter_prompt,
)
from app.services.llm.streamlined_prompt_engineering import (
    build_streamlined_system_prompt,
    build_streamlined_first_chapter_prompt,
    build_streamlined_prompt,
)


def create_sample_state() -> AdventureState:
    """Create a sample AdventureState for testing."""
    state = AdventureState(
        story_category="festival_of_lights_and_colors",
        lesson_topic="Farm Animals",
        story_length=10,
        current_chapter_id="start",
        current_chapter_number=1,
        chapters=[],
        planned_chapter_types=[ChapterType.STORY] * 10,  # All STORY for simplicity
        selected_narrative_elements={
            "setting_types": "Illuminated bridges arched over canals of sparkling water",
            "character_archetypes": "Friendly festival guardians who ensure laughter and harmony",
            "story_rules": "Selfish acts cause lanterns to dim and colors to fade",
        },
        selected_sensory_details={
            "visuals": "Reflective ribbons dancing in the breeze under starlit skies",
            "sounds": "Gentle humming of glowing insects drawn to the colorful lights",
            "smells": "Warm fragrance of toasted nuts and honey filling the night air",
        },
        selected_theme="Celebrating diversity through the brilliant spectrum of colors",
        selected_moral_teaching="Courage helps us step into the unknown without losing hope",
        selected_plot_twist="A hidden pattern in the festival lights reveals an ancient message",
        current_storytelling_phase="Exposition",
        metadata={},
        correct_lesson_answers=0,
        total_lessons=0,
    )
    return state


def compare_prompts() -> None:
    """Compare original and streamlined prompts."""
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("test_streamlined_prompts")

    # Create a sample state
    state = create_sample_state()

    # Generate original prompts
    original_system_prompt = build_system_prompt(state)
    original_user_prompt = build_user_prompt(state)

    # Generate streamlined prompts
    streamlined_system_prompt = build_streamlined_system_prompt(state)
    streamlined_user_prompt = build_streamlined_first_chapter_prompt(state)

    # Print comparison
    logger.info("\n" + "=" * 80)
    logger.info("PROMPT COMPARISON")
    logger.info("=" * 80)

    # System prompt comparison
    logger.info("\nORIGINAL SYSTEM PROMPT:")
    logger.info("-" * 40)
    logger.info(original_system_prompt)

    logger.info("\nSTREAMLINED SYSTEM PROMPT:")
    logger.info("-" * 40)
    logger.info(streamlined_system_prompt)

    # User prompt comparison
    logger.info("\nORIGINAL USER PROMPT:")
    logger.info("-" * 40)
    logger.info(original_user_prompt)

    logger.info("\nSTREAMLINED USER PROMPT:")
    logger.info("-" * 40)
    logger.info(streamlined_user_prompt)

    # Highlight key improvements
    logger.info("\n" + "=" * 80)
    logger.info("KEY IMPROVEMENTS")
    logger.info("=" * 80)
    logger.info("""
1. Consolidated CRITICAL RULES:
   - Original: Multiple separate CRITICAL RULES sections
   - Streamlined: Single comprehensive CRITICAL RULES section

2. Integrated Agency Instructions:
   - Original: Agency instructions spread across multiple sections
   - Streamlined: Agency instructions consolidated with critical rules

3. Improved Organization:
   - Original: Scattered related information
   - Streamlined: Logical grouping of related instructions

4. Reduced Redundancy:
   - Original: Repeated instructions in multiple places
   - Streamlined: Each instruction appears only once

5. Enhanced Clarity:
   - Original: Complex nested instructions
   - Streamlined: Clear, categorized guidance
""")


if __name__ == "__main__":
    compare_prompts()
