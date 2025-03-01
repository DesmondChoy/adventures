"""
Test script to verify the integration of further streamlined prompts.

This script creates a sample AdventureState for the first chapter and
generates content using the LLM service to confirm that the further streamlined
prompts are being used correctly.
"""

import sys
import os
import asyncio
import logging
from typing import Dict, Any

# Add the parent directory to the path so we can import the app modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from app.models.story import AdventureState, ChapterType
from app.services.llm import LLMService


async def test_further_streamlined_integration():
    """Test the integration of further streamlined prompts."""
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("test_further_streamlined")

    # Create a sample state for the first chapter
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

    # Initialize the LLM service
    llm_service = LLMService()

    # Load story configuration
    story_config = {
        "name": "Festival of Lights and Colors",
        "description": "A vibrant celebration where colors and light reveal deeper truths",
    }

    logger.info("Generating first chapter content using further streamlined prompts...")

    # Generate content (collect just a small sample to verify it's working)
    content = ""
    sample_size = 200  # Just get the first 200 characters to verify
    chars_collected = 0

    try:
        async for chunk in llm_service.generate_chapter_stream(
            story_config=story_config,
            state=state,
            question=None,
            previous_lessons=None,
        ):
            content += chunk
            chars_collected += len(chunk)
            if chars_collected >= sample_size:
                break
    except Exception as e:
        logger.error(f"Error generating content: {e}")
        return

    logger.info("\n=== FURTHER STREAMLINED INTEGRATION TEST RESULTS ===")
    logger.info("First chapter content sample:")
    logger.info(content[:sample_size] + "...")
    logger.info("=================================================")
    logger.info("Integration test completed successfully!")
    logger.info(
        "Check the logs above to verify that further streamlined prompts were used."
    )


if __name__ == "__main__":
    asyncio.run(test_further_streamlined_integration())
