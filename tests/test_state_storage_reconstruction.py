"""
Test State Storage Reconstruction

This script tests the state reconstruction functionality with uppercase chapter types.
It creates a test state with uppercase chapter types, stores it, retrieves it,
and verifies that the chapter types are correctly converted to lowercase during reconstruction.
"""

import asyncio
import logging
import sys
import os
import json
from typing import Dict, Any

# Add the parent directory to the path so we can import the app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.state_storage_service import StateStorageService
from app.services.adventure_state_manager import AdventureStateManager
from app.models.story import ChapterType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("test_state_storage_reconstruction")


async def create_test_state_with_uppercase_types() -> Dict[str, Any]:
    """Create a test state with uppercase chapter types.

    Returns:
        A dictionary containing the test state with uppercase chapter types
    """
    logger.info("Creating test state with uppercase chapter types")

    # Create a basic test state with uppercase chapter types
    test_state = {
        "current_chapter_id": "chapter_10",
        "story_length": 10,
        "selected_narrative_elements": {
            "settings": "Enchanted Forest",
            "characters": "Brave Knight",
            "objects": "Magic Sword",
            "events": "Dragon Attack",
        },
        "selected_sensory_details": {
            "visuals": "Sparkling lights",
            "sounds": "Rustling leaves",
            "smells": "Fresh pine",
            "textures": "Rough bark",
        },
        "selected_theme": "Friendship",
        "selected_moral_teaching": "Honesty is the best policy",
        "selected_plot_twist": "The forest guardian was the old friend all along",
        "current_storytelling_phase": "Conclusion",
        # Include chapters with uppercase chapter types
        "chapters": [
            {
                "chapter_number": 1,
                "chapter_type": "STORY",  # Uppercase
                "content": "This is chapter 1.",
                "chapter_content": {
                    "content": "This is chapter 1.",
                    "choices": [
                        {"text": "Option 1", "next_chapter": "chapter_1_0"},
                        {"text": "Option 2", "next_chapter": "chapter_1_1"},
                        {"text": "Option 3", "next_chapter": "chapter_1_2"},
                    ],
                },
            },
            {
                "chapter_number": 2,
                "chapter_type": "LESSON",  # Uppercase
                "content": "This is chapter 2.",
                "chapter_content": {
                    "content": "This is chapter 2.",
                    "choices": [],
                },
                "question": {
                    "question": "What is the moral of the story?",
                    "answers": [
                        {"text": "Honesty is the best policy", "is_correct": True},
                        {"text": "Might makes right", "is_correct": False},
                    ],
                    "explanation": "The story teaches us that honesty leads to trust and friendship.",
                },
            },
            {
                "chapter_number": 3,
                "chapter_type": "STORY",  # Uppercase
                "content": "This is chapter 3.",
                "chapter_content": {
                    "content": "This is chapter 3.",
                    "choices": [
                        {"text": "Option 1", "next_chapter": "chapter_3_0"},
                        {"text": "Option 2", "next_chapter": "chapter_3_1"},
                        {"text": "Option 3", "next_chapter": "chapter_3_2"},
                    ],
                },
            },
            {
                "chapter_number": 4,
                "chapter_type": "LESSON",  # Uppercase
                "content": "This is chapter 4.",
                "chapter_content": {
                    "content": "This is chapter 4.",
                    "choices": [],
                },
            },
            {
                "chapter_number": 5,
                "chapter_type": "REFLECT",  # Uppercase
                "content": "This is chapter 5.",
                "chapter_content": {
                    "content": "This is chapter 5.",
                    "choices": [],
                },
            },
            {
                "chapter_number": 6,
                "chapter_type": "STORY",  # Uppercase
                "content": "This is chapter 6.",
                "chapter_content": {
                    "content": "This is chapter 6.",
                    "choices": [
                        {"text": "Option 1", "next_chapter": "chapter_6_0"},
                        {"text": "Option 2", "next_chapter": "chapter_6_1"},
                        {"text": "Option 3", "next_chapter": "chapter_6_2"},
                    ],
                },
            },
            {
                "chapter_number": 7,
                "chapter_type": "LESSON",  # Uppercase
                "content": "This is chapter 7.",
                "chapter_content": {
                    "content": "This is chapter 7.",
                    "choices": [],
                },
            },
            {
                "chapter_number": 8,
                "chapter_type": "STORY",  # Uppercase
                "content": "This is chapter 8.",
                "chapter_content": {
                    "content": "This is chapter 8.",
                    "choices": [
                        {"text": "Option 1", "next_chapter": "chapter_8_0"},
                        {"text": "Option 2", "next_chapter": "chapter_8_1"},
                        {"text": "Option 3", "next_chapter": "chapter_8_2"},
                    ],
                },
            },
            {
                "chapter_number": 9,
                "chapter_type": "LESSON",  # Uppercase
                "content": "This is chapter 9.",
                "chapter_content": {
                    "content": "This is chapter 9.",
                    "choices": [],
                },
            },
            {
                "chapter_number": 10,
                "chapter_type": "CONCLUSION",  # Uppercase
                "content": "This is a test conclusion chapter.",
                "chapter_content": {
                    "content": "This is a test conclusion chapter.",
                    "choices": [],
                },
            },
        ],
        # Add chapter summaries
        "chapter_summaries": [
            f"Chapter {i}: Summary for chapter {i}." for i in range(1, 11)
        ],
        # Add planned chapter types with uppercase
        "planned_chapter_types": [
            "STORY",
            "LESSON",
            "STORY",
            "LESSON",
            "REFLECT",
            "STORY",
            "LESSON",
            "STORY",
            "LESSON",
            "CONCLUSION",
        ],
        # Add metadata
        "metadata": {
            "agency": {"name": "Magic Sword", "type": "item", "references": []}
        },
    }

    return test_state


async def test_state_reconstruction():
    """Test the state reconstruction functionality with uppercase chapter types."""
    try:
        # Create instances of the services
        state_storage_service = StateStorageService()
        state_manager = AdventureStateManager()

        # Create a test state with uppercase chapter types
        test_state = await create_test_state_with_uppercase_types()
        logger.info("Created test state with uppercase chapter types")

        # Store the state
        state_id = await state_storage_service.store_state(test_state)
        logger.info(f"Stored state with ID: {state_id}")

        # Verify the state is in the memory cache
        logger.info(
            f"Memory cache keys: {list(state_storage_service._memory_cache.keys())}"
        )

        if state_id in state_storage_service._memory_cache:
            logger.info("State found in memory cache ✅")
        else:
            logger.error("State not found in memory cache ❌")
            return False

        # Retrieve the state
        stored_state = await state_storage_service.get_state(state_id)

        if stored_state:
            logger.info("Retrieved state from storage ✅")

            # Verify the chapter types are still uppercase in the stored state
            for chapter in stored_state["chapters"]:
                chapter_type = chapter.get("chapter_type", "")
                if chapter_type.isupper():
                    logger.info(
                        f"Chapter {chapter['chapter_number']} type is uppercase: {chapter_type} ✅"
                    )
                else:
                    logger.error(
                        f"Chapter {chapter['chapter_number']} type is not uppercase: {chapter_type} ❌"
                    )
                    return False

            # Verify the planned chapter types are still uppercase in the stored state
            for i, chapter_type in enumerate(stored_state["planned_chapter_types"]):
                if chapter_type.isupper():
                    logger.info(
                        f"Planned chapter type {i + 1} is uppercase: {chapter_type} ✅"
                    )
                else:
                    logger.error(
                        f"Planned chapter type {i + 1} is not uppercase: {chapter_type} ❌"
                    )
                    return False
        else:
            logger.error("Failed to retrieve state from storage ❌")
            return False

        # Reconstruct the state using the AdventureStateManager
        reconstructed_state = await state_manager.reconstruct_state_from_storage(
            stored_state
        )

        if reconstructed_state:
            logger.info("Successfully reconstructed state ✅")

            # Verify the chapter types are now lowercase in the reconstructed state
            for chapter in reconstructed_state.chapters:
                chapter_type_value = chapter.chapter_type.value
                if chapter_type_value.islower():
                    logger.info(
                        f"Chapter {chapter.chapter_number} type is lowercase: {chapter_type_value} ✅"
                    )
                else:
                    logger.error(
                        f"Chapter {chapter.chapter_number} type is not lowercase: {chapter_type_value} ❌"
                    )
                    return False

            # Verify the planned chapter types are now lowercase in the reconstructed state
            for i, chapter_type in enumerate(reconstructed_state.planned_chapter_types):
                if chapter_type.islower():
                    logger.info(
                        f"Planned chapter type {i + 1} is lowercase: {chapter_type} ✅"
                    )
                else:
                    logger.error(
                        f"Planned chapter type {i + 1} is not lowercase: {chapter_type} ❌"
                    )
                    return False

            # Format the adventure summary data
            summary_data = await state_manager.format_adventure_summary_data(
                reconstructed_state
            )
            logger.info("Successfully formatted adventure summary data ✅")

            # Save the summary data to a file for inspection
            with open("tests/case_sensitivity_summary_data.json", "w") as f:
                json.dump(summary_data, f, indent=2)
            logger.info(
                "Saved summary data to tests/case_sensitivity_summary_data.json ✅"
            )

            logger.info("All tests passed successfully ✅")
            return True
        else:
            logger.error("Failed to reconstruct state ❌")
            return False

    except Exception as e:
        logger.error(f"Error in test: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    """Run the test."""
    logger.info("Starting state reconstruction test with uppercase chapter types")

    # Test the state reconstruction
    result = await test_state_reconstruction()

    # Print overall results
    if result:
        logger.info("✅ Test passed successfully! ✅")
        return 0
    else:
        logger.error("❌ Test failed ❌")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
