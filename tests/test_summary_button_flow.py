"""
Test Summary Button Flow

This script tests the "Take a Trip Down Memory Lane" button functionality by:
1. Creating a test state (either from simulation or synthetic data)
2. Storing the state in StateStorageService
3. Retrieving the state
4. Reconstructing the adventure state
5. Formatting the summary data
6. Verifying all data is correctly formatted

By default, this uses realistic data generated by generate_all_chapters.py.
Use the --synthetic flag to use synthetic hardcoded data instead.

Usage:
    python tests/test_summary_button_flow.py [options]

Options:
    --synthetic     Use synthetic hardcoded state instead of realistic state
    --file PATH     Load state from a file
    --category CAT  Use specific story category
    --topic TOPIC   Use specific lesson topic
    --compare       Compare synthetic and realistic states
"""

import asyncio
import logging
import sys
import os
import uuid
import json
import argparse
from typing import Dict, Any, Optional

# Add the parent directory to the path so we can import the app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.state_storage_service import StateStorageService
from app.services.adventure_state_manager import AdventureStateManager
from app.models.story import ChapterType
from tests.utils.generate_test_state import (
    generate_test_state,
    compare_state_structures,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("test_summary_button")


async def create_test_state(
    use_synthetic_state: bool = False,
    state_file: Optional[str] = None,
    story_category: Optional[str] = None,
    lesson_topic: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a test state with all required fields.

    Args:
        use_synthetic_state: If True, use a synthetic hardcoded state instead of generate_test_state
        state_file: Optional path to a state file to load
        story_category: Optional story category to use
        lesson_topic: Optional lesson topic to use

    Returns:
        A dictionary containing the test state
    """
    # Track the source of the state for debugging
    state_source = "unknown"

    if state_file:
        # Load state from file
        logger.info(f"Loading test state from file: {state_file}")
        try:
            with open(state_file, "r") as f:
                state_source = f"file:{state_file}"
                state_data = json.load(f)
                logger.info(f"Successfully loaded state from file: {state_file}")
                return state_data
        except Exception as e:
            logger.error(f"Error loading state from file: {e}")
            logger.info("Falling back to generated state")

    if not use_synthetic_state:
        # Use generate_test_state to create a realistic state (default behavior)
        logger.info("Creating realistic test state using generate_test_state")
        state_source = "realistic:generate_test_state"
        state_data = await generate_test_state(
            story_category=story_category,
            lesson_topic=lesson_topic,
            use_mock=False,  # Use actual simulation by default
        )
        logger.info(f"State source: {state_source}")
        return state_data

    # Use the synthetic test state (only if explicitly requested)
    logger.info("Creating synthetic test state (hardcoded values)")
    state_source = "synthetic:hardcoded"
    return {
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
        # Include all chapters 1-10 with lowercase chapter types
        "chapters": [
            {
                "chapter_number": 1,
                "chapter_type": "story",
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
                "chapter_type": "lesson",
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
                "chapter_type": "story",
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
                "chapter_type": "lesson",
                "content": "This is chapter 4.",
                "chapter_content": {
                    "content": "This is chapter 4.",
                    "choices": [],
                },
            },
            {
                "chapter_number": 5,
                "chapter_type": "reflect",
                "content": "This is chapter 5.",
                "chapter_content": {
                    "content": "This is chapter 5.",
                    "choices": [],
                },
            },
            {
                "chapter_number": 6,
                "chapter_type": "story",
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
                "chapter_type": "lesson",
                "content": "This is chapter 7.",
                "chapter_content": {
                    "content": "This is chapter 7.",
                    "choices": [],
                },
            },
            {
                "chapter_number": 8,
                "chapter_type": "story",
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
                "chapter_type": "lesson",
                "content": "This is chapter 9.",
                "chapter_content": {
                    "content": "This is chapter 9.",
                    "choices": [],
                },
            },
            {
                "chapter_number": 10,
                "chapter_type": "conclusion",
                "content": "This is a test conclusion chapter.",
                "chapter_content": {
                    "content": "This is a test conclusion chapter.",
                    "choices": [],
                },
            },
        ],
        # Add chapter summaries for all chapters
        "chapter_summaries": [
            "Chapter 1: The Beginning - The hero started their journey.",
            "Chapter 2: The First Lesson - The hero learned about honesty.",
            "Chapter 3: The Challenge - The hero faced their first challenge.",
            "Chapter 4: The Second Lesson - The hero learned about courage.",
            "Chapter 5: The Reflection - The hero reflected on their journey so far.",
            "Chapter 6: The Twist - The hero discovered a surprising truth.",
            "Chapter 7: The Third Lesson - The hero learned about friendship.",
            "Chapter 8: The Climax - The hero faced the final challenge.",
            "Chapter 9: The Fourth Lesson - The hero learned about perseverance.",
            "Chapter 10: The Adventure Concludes - The hero returned home with newfound wisdom.",
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
        # Add planned chapter types
        "planned_chapter_types": [
            "story",
            "lesson",
            "story",
            "lesson",
            "reflect",
            "story",
            "lesson",
            "story",
            "lesson",
            "conclusion",
        ],
        # Add metadata
        "metadata": {
            "agency": {"name": "Magic Sword", "type": "item", "references": []}
        },
    }


async def test_summary_button_flow(
    use_synthetic_state: bool = False,
    state_file: Optional[str] = None,
    story_category: Optional[str] = None,
    lesson_topic: Optional[str] = None,
):
    """Test the entire flow from storing a state to retrieving and reconstructing it.

    Args:
        use_synthetic_state: If True, use a synthetic hardcoded state instead of a realistic one
        state_file: Optional path to a state file to load
        story_category: Optional story category to use
        lesson_topic: Optional lesson topic to use
    """
    try:
        # Create instances of the services
        state_storage_service = StateStorageService()
        state_manager = AdventureStateManager()

        # Create a test state
        test_state = await create_test_state(
            use_synthetic_state=use_synthetic_state,
            state_file=state_file,
            story_category=story_category,
            lesson_topic=lesson_topic,
        )
        logger.info("Created test state")

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
            logger.info(f"State keys: {list(stored_state.keys())}")
        else:
            logger.error("Failed to retrieve state from storage ❌")
            return False

        # Reconstruct the state using the AdventureStateManager
        reconstructed_state = await state_manager.reconstruct_state_from_storage(
            stored_state
        )

        if reconstructed_state:
            logger.info("Successfully reconstructed state ✅")

            # Format the adventure summary data
            summary_data = state_manager.format_adventure_summary_data(
                reconstructed_state
            )
            logger.info("Successfully formatted adventure summary data ✅")

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
            with open("tests/summary_data.json", "w") as f:
                json.dump(summary_data, f, indent=2)
            logger.info("Saved summary data to tests/summary_data.json ✅")

            logger.info("All summary data verified successfully ✅")
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
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Test the summary button flow")
    parser.add_argument(
        "--synthetic",
        action="store_true",
        help="Use a synthetic hardcoded state instead of a realistic generated state",
    )
    parser.add_argument(
        "--file",
        type=str,
        help="Path to a state file to load",
    )
    parser.add_argument(
        "--category",
        type=str,
        help="Story category to use",
    )
    parser.add_argument(
        "--topic",
        type=str,
        help="Lesson topic to use",
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        help="Compare synthetic and realistic states",
    )
    args = parser.parse_args()

    logger.info("Starting summary button flow test")

    if args.compare:
        # Compare synthetic and realistic states
        logger.info("Comparing synthetic and realistic states")
        synthetic_state = await create_test_state(use_synthetic_state=True)
        realistic_state = await create_test_state(use_synthetic_state=False)

        differences = compare_state_structures(synthetic_state, realistic_state)

        logger.info(f"Found {len(differences)} differences between states")
        for diff in differences:
            logger.info(f"  - {diff}")

        # Save both states for inspection
        with open("tests/synthetic_state.json", "w") as f:
            json.dump(synthetic_state, f, indent=2)
        with open("tests/realistic_state.json", "w") as f:
            json.dump(realistic_state, f, indent=2)

        logger.info(
            "Saved states to tests/synthetic_state.json and tests/realistic_state.json"
        )
        return 0

    # Test the entire flow
    result = await test_summary_button_flow(
        use_synthetic_state=args.synthetic,
        state_file=args.file,
        story_category=args.category,
        lesson_topic=args.topic,
    )

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
