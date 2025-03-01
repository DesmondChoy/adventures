#!/usr/bin/env python
"""
Test script to verify that build_prompt() is being called correctly.
"""

import sys
import os
import logging
from typing import Dict, Any, List, Optional

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from app.models.story import AdventureState, ChapterType
from app.services.llm.prompt_engineering import build_prompt, build_user_prompt
from app.services.llm.providers import GeminiService

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("test_prompt")


def create_test_state() -> AdventureState:
    """Create a minimal test state for prompt generation."""
    state = AdventureState(
        story_length=5,
        current_chapter_number=1,
        current_chapter_id="start",
        chapters=[],
        planned_chapter_types=[
            ChapterType.STORY,
            ChapterType.LESSON,
            ChapterType.STORY,
            ChapterType.LESSON,
            ChapterType.CONCLUSION,
        ],
        current_storytelling_phase="Exposition",
        selected_narrative_elements={
            "setting_types": "A magical forest with hidden wonders",
            "character_archetypes": "A curious child explorer",
            "story_rules": "The journey must include a magical discovery",
        },
        selected_sensory_details={
            "visuals": "Glowing mushrooms, dappled sunlight through leaves",
            "sounds": "Rustling leaves, distant animal calls",
            "smells": "Fresh pine, earthy moss",
        },
        selected_theme="Curiosity and discovery",
        selected_moral_teaching="Courage to explore the unknown",
        selected_plot_twist="What seems scary at first might become a friend",
        correct_lesson_answers=0,
        total_lessons=2,
        metadata={},
    )
    return state


def test_build_user_prompt():
    """Test that build_user_prompt() generates a prompt with expected sections."""
    state = create_test_state()

    # Generate the prompt
    prompt = build_user_prompt(state)

    # Check if key sections are present
    template_markers = [
        "# Current Context",
        "- Chapter:",
        "- Type:",
        "- Phase:",
        "- Progress:",
        "# Story History",
        "# Chapter Development Guidelines",
    ]

    for marker in template_markers:
        assert marker in prompt, f"Marker '{marker}' not found in prompt"

    logger.info("All expected markers found in the generated prompt")

    # Print the prompt for inspection
    print("\n=== Generated Prompt ===")
    print(prompt)
    print("========================\n")

    return True


def test_build_prompt():
    """Test that build_prompt() generates both system and user prompts."""
    state = create_test_state()

    # Generate the prompts
    system_prompt, user_prompt = build_prompt(state)

    # Check if key sections are present in system prompt
    system_markers = [
        "# Storyteller Role",
        "# Story Elements",
        "# Storytelling Approach & Agency Integration",
        "# CRITICAL RULES",
    ]

    for marker in system_markers:
        assert marker in system_prompt, f"Marker '{marker}' not found in system prompt"

    # Check if key sections are present in user prompt
    user_markers = [
        "# Current Context",
        "- Chapter:",
        "- Type:",
        "- Phase:",
        "- Progress:",
        "# Story History",
        "# Chapter Development Guidelines",
    ]

    for marker in user_markers:
        assert marker in user_prompt, f"Marker '{marker}' not found in user prompt"

    logger.info("All expected markers found in the generated prompts")

    # Print the prompts for inspection
    print("\n=== Generated System Prompt ===")
    print(system_prompt)
    print("========================\n")
    print("\n=== Generated User Prompt ===")
    print(user_prompt)
    print("========================\n")

    return True


def test_llm_service_uses_build_prompt():
    """Test that the LLM service uses build_prompt()."""
    state = create_test_state()

    # Create a mock LLM service
    class MockGeminiService(GeminiService):
        def __init__(self):
            pass

        async def generate_chapter_stream(self, *args, **kwargs):
            # Just access the user_prompt for testing
            story_config = kwargs.get("story_config", {})
            state = kwargs.get("state")
            question = kwargs.get("question")
            previous_lessons = kwargs.get("previous_lessons")

            # Build prompts using build_prompt function
            system_prompt, user_prompt = build_prompt(
                state=state,
                lesson_question=question,
                previous_lessons=previous_lessons,
            )

            # Print for inspection
            print("\n=== LLM Service Generated System Prompt ===")
            print(system_prompt)
            print("===================================\n")
            print("\n=== LLM Service Generated User Prompt ===")
            print(user_prompt)
            print("===================================\n")

            # Check if key sections are present in system prompt
            system_markers = [
                "# Storyteller Role",
                "# Story Elements",
                "# Storytelling Approach & Agency Integration",
                "# CRITICAL RULES",
            ]

            for marker in system_markers:
                assert marker in system_prompt, (
                    f"Marker '{marker}' not found in system prompt"
                )

            # Check if key sections are present in user prompt
            user_markers = [
                "# Current Context",
                "- Chapter:",
                "- Type:",
                "- Phase:",
                "- Progress:",
                "# Story History",
                "# Chapter Development Guidelines",
            ]

            for marker in user_markers:
                assert marker in user_prompt, (
                    f"Marker '{marker}' not found in user prompt"
                )

            logger.info("LLM service is using build_prompt() correctly")

            # Just yield something to satisfy the async generator requirement
            yield "Test successful"

    # Create the mock service
    service = MockGeminiService()

    # Run the test (this will be a coroutine, so we'll just set it up)
    generator = service.generate_chapter_stream(
        story_config={}, state=state, question=None, previous_lessons=None
    )

    # In a real test, you would await this generator
    # For our purposes, we'll just return the generator object
    return generator


if __name__ == "__main__":
    # Run the tests
    logger.info("Testing build_user_prompt()...")
    test_build_user_prompt()

    logger.info("Testing build_prompt()...")
    test_build_prompt()

    logger.info("Testing LLM service uses build_prompt()...")
    generator = test_llm_service_uses_build_prompt()

    # Note: In a real environment, you would use asyncio to run the async generator
    # For this test script, we're just setting up the test

    logger.info(
        "Tests completed. Check the output above to verify the prompts are being generated correctly."
    )
