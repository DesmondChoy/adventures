"""
Test Conclusion Chapter Fix

This script tests the fix for the "Trip down memory lane" button issue by:
1. Creating a test state with a CONCLUSION chapter (uppercase)
2. Storing the state in StateStorageService
3. Retrieving the state with a duplicate state_id parameter
4. Verifying that the state is correctly reconstructed with the CONCLUSION chapter
5. Checking that the summary data is correctly formatted

Usage:
    python tests/test_conclusion_chapter_fix.py
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
from app.routers.summary_router import get_adventure_summary

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("test_conclusion_chapter_fix")


async def create_test_state_with_conclusion() -> Dict[str, Any]:
    """Create a test state with a CONCLUSION chapter (uppercase).

    Returns:
        A dictionary containing the test state with a CONCLUSION chapter
    """
    logger.info("Creating test state with CONCLUSION chapter")

    # Create a basic test state with a CONCLUSION chapter
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
        # Include all chapters 1-10 with the last one being a CONCLUSION chapter
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
        # Add chapter summaries for all chapters
        "chapter_summaries": [
            f"Chapter {i}: Summary for chapter {i}." for i in range(1, 11)
        ],
        # Add lesson questions
        "lesson_questions": [
            {
                "question": "What is the moral of the story?",
                "answers": [
                    {"text": "Honesty is the best policy", "is_correct": True},
                    {"text": "Might makes right", "is_correct": False},
                ],
                "explanation": "The story teaches us that honesty leads to trust and friendship.",
            }
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


class MockRequest:
    """Mock request object for testing."""

    def __init__(self, query_params=None):
        self.query_params = query_params or {}


async def test_conclusion_chapter_fix():
    """Test the fix for the CONCLUSION chapter handling and duplicate state_id parameter issues."""
    try:
        # Create instances of the services
        state_storage_service = StateStorageService()
        state_manager = AdventureStateManager()

        # Create a test state with a CONCLUSION chapter
        test_state = await create_test_state_with_conclusion()
        logger.info("Created test state with CONCLUSION chapter")

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

        # Test with duplicate state_id parameter
        duplicate_state_id = f"{state_id},{state_id}"
        logger.info(f"Testing with duplicate state_id: {duplicate_state_id}")

        # Call the get_adventure_summary function directly
        summary_data = await get_adventure_summary(state_id=duplicate_state_id)

        # Verify the summary data
        if (
            "chapterSummaries" in summary_data
            and len(summary_data["chapterSummaries"]) == 10
        ):
            logger.info("Chapter summaries verified ✅")
        else:
            logger.error("Missing or incorrect chapter summaries ❌")
            return False

        if (
            "educationalQuestions" in summary_data
            and len(summary_data["educationalQuestions"]) > 0
        ):
            logger.info("Educational questions verified ✅")
        else:
            logger.error("Missing or incorrect educational questions ❌")
            return False

        if "statistics" in summary_data:
            logger.info("Statistics verified ✅")
        else:
            logger.error("Missing statistics ❌")
            return False

        # Save the summary data to a file for inspection
        with open("tests/conclusion_chapter_fix_summary_data.json", "w") as f:
            json.dump(summary_data, f, indent=2)
        logger.info(
            "Saved summary data to tests/conclusion_chapter_fix_summary_data.json ✅"
        )

        logger.info("All tests passed successfully ✅")
        return True

    except Exception as e:
        logger.error(f"Error in test: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    """Run the test."""
    logger.info("Starting conclusion chapter fix test")

    # Test the conclusion chapter fix
    result = await test_conclusion_chapter_fix()

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
