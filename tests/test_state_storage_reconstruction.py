import asyncio
import logging
import sys
import os
import uuid
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
logger = logging.getLogger("test_state_storage")


async def create_test_state() -> Dict[str, Any]:
    """Create a test state with all required fields."""
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
        # Include all chapters 1-10
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
        # Add some lesson questions
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
        "metadata": {
            "agency": {"name": "Magic Sword", "type": "item", "references": []}
        },
    }


async def test_state_storage_and_reconstruction():
    """Test storing a state and reconstructing it."""
    try:
        # Create instances of the services
        state_storage_service = StateStorageService()
        state_manager = AdventureStateManager()

        # Create a test state
        test_state = await create_test_state()
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

            # Verify key properties
            logger.info("Verifying reconstructed state properties:")

            # Check narrative elements
            narrative_elements = reconstructed_state.selected_narrative_elements
            logger.info(f"Narrative elements: {narrative_elements}")
            if all(
                k in narrative_elements
                for k in ["settings", "characters", "objects", "events"]
            ):
                logger.info("Narrative elements verified ✅")
            else:
                logger.error("Missing narrative elements ❌")
                return False

            # Check sensory details
            sensory_details = reconstructed_state.selected_sensory_details
            logger.info(f"Sensory details: {sensory_details}")
            if all(
                k in sensory_details
                for k in ["visuals", "sounds", "smells", "textures"]
            ):
                logger.info("Sensory details verified ✅")
            else:
                logger.error("Missing sensory details ❌")
                return False

            # Check required string fields
            if (
                reconstructed_state.selected_theme
                and reconstructed_state.selected_moral_teaching
                and reconstructed_state.selected_plot_twist
            ):
                logger.info("Required string fields verified ✅")
            else:
                logger.error("Missing required string fields ❌")
                return False

            # Check chapters
            if reconstructed_state.chapters and len(reconstructed_state.chapters) > 0:
                logger.info(
                    f"Chapters verified: {len(reconstructed_state.chapters)} chapters ✅"
                )

                # Check if there's a CONCLUSION chapter
                conclusion_chapters = [
                    ch
                    for ch in reconstructed_state.chapters
                    if ch.chapter_type == ChapterType.CONCLUSION
                ]
                if conclusion_chapters:
                    logger.info("CONCLUSION chapter found ✅")
                else:
                    logger.error("No CONCLUSION chapter found ❌")
                    return False
            else:
                logger.error("No chapters found ❌")
                return False

            logger.info("All state properties verified successfully ✅")
            return True
        else:
            logger.error("Failed to reconstruct state ❌")
            return False

    except Exception as e:
        logger.error(f"Error in test: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


async def test_with_random_state_id():
    """Test retrieving a state with a random ID (should fail gracefully)."""
    try:
        # Create instances of the services
        state_storage_service = StateStorageService()
        state_manager = AdventureStateManager()

        # Generate a random state ID
        random_state_id = str(uuid.uuid4())
        logger.info(f"Testing with random state ID: {random_state_id}")

        # Try to retrieve the state
        stored_state = await state_storage_service.get_state(random_state_id)

        if stored_state is None:
            logger.info("Correctly returned None for non-existent state ID ✅")
        else:
            logger.error("Unexpectedly found a state with random ID ❌")
            return False

        # Try to reconstruct the state (should handle None gracefully)
        reconstructed_state = await state_manager.reconstruct_state_from_storage(
            stored_state
        )

        if reconstructed_state is None:
            logger.info("Correctly handled None state in reconstruction ✅")
            return True
        else:
            logger.error("Unexpectedly reconstructed a state from None ❌")
            return False

    except Exception as e:
        logger.error(f"Error in random ID test: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    logger.info("Starting state storage and reconstruction tests")

    # Test storing and reconstructing a state
    storage_result = await test_state_storage_and_reconstruction()

    # Test with a random state ID
    random_id_result = await test_with_random_state_id()

    # Print overall results
    if storage_result and random_id_result:
        logger.info("✅ All tests passed successfully! ✅")
        return 0
    else:
        logger.error("❌ Some tests failed ❌")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
