import asyncio
import json
import logging
import os
import sys
import uuid
from typing import Dict, Any, List

# Add the parent directory to the path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.story import AdventureState, ChapterType
from app.services.state_storage_service import StateStorageService
from app.routers.summary_router import store_adventure_state, get_adventure_summary

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("test_chapter_summary_fix")


async def create_test_state() -> Dict[str, Any]:
    """Create a test state with a CONCLUSION chapter but no summary."""
    # Create a minimal state with 3 chapters: STORY, LESSON, CONCLUSION
    state_data = {
        "story_length": 3,
        "current_chapter_number": 3,
        "planned_chapter_types": ["story", "lesson", "conclusion"],
        "current_storytelling_phase": "resolution",
        "selected_narrative_elements": {
            "setting": "A magical forest",
            "protagonist": "A young explorer",
            "antagonist": "A mischievous sprite",
            "conflict": "The sprite has hidden the explorer's map",
        },
        "selected_sensory_details": {
            "visual": "Sunlight filtering through dense foliage",
            "auditory": "Birds chirping and leaves rustling",
            "tactile": "Cool moss underfoot",
            "olfactory": "The scent of pine and wildflowers",
            "gustatory": "Sweet berries growing along the path",
        },
        "selected_theme": "Friendship and cooperation",
        "selected_moral_teaching": "Working together solves problems",
        "selected_plot_twist": "The sprite was actually trying to help",
        "chapter_summaries": [],  # Empty summaries - should be generated
        "summary_chapter_titles": [],  # Empty titles - should be generated
        "lesson_questions": [
            {
                "question": "What is the main theme of this story?",
                "answers": [
                    {"text": "Competition", "is_correct": False},
                    {"text": "Friendship", "is_correct": True},
                    {"text": "Revenge", "is_correct": False},
                ],
                "chosen_answer": "Friendship",
                "is_correct": True,
                "explanation": "The story emphasizes how friendship and cooperation help solve problems.",
            }
        ],
        "metadata": {"agency": "Explorer's compass"},
        "chapters": [
            {
                "chapter_number": 1,
                "chapter_type": "STORY",
                "content": "Once upon a time, a young explorer ventured into a magical forest. The trees towered above, their leaves creating a dappled pattern of sunlight on the forest floor. Birds sang cheerfully, and the scent of pine and wildflowers filled the air. The explorer carried a special compass, a family heirloom that always pointed toward adventure.",
                "response": {
                    "choice_text": "Follow the path deeper into the forest",
                    "chosen_path": "path_deeper",
                },
            },
            {
                "chapter_number": 2,
                "chapter_type": "LESSON",
                "content": "As the explorer walked, they came across a clearing where a lesson awaited. The lesson was about friendship and how working together can solve problems that seem impossible alone. The explorer learned that even those who seem like adversaries might actually be potential friends.",
                "question": {
                    "question": "What is the main theme of this story?",
                    "answers": [
                        {"text": "Competition", "is_correct": False},
                        {"text": "Friendship", "is_correct": True},
                        {"text": "Revenge", "is_correct": False},
                    ],
                    "explanation": "The story emphasizes how friendship and cooperation help solve problems.",
                },
                "response": {"chosen_answer": "Friendship", "is_correct": True},
            },
            {
                "chapter_number": 3,
                "chapter_type": "CONCLUSION",
                "content": "Finally, the explorer discovered that the mischievous sprite who had hidden the map was actually trying to protect them from a dangerous part of the forest. The sprite revealed a safer route home, and they became friends. The explorer learned that appearances can be deceiving, and that friendship can be found in unexpected places. With the sprite's help, the explorer found their way home, carrying not just their compass but a new friendship as well.",
            },
        ],
    }
    return state_data


async def test_store_adventure_state():
    """Test that store_adventure_state generates missing summaries."""
    logger.info("Creating test state...")
    state_data = await create_test_state()

    # Verify the state has no summaries initially
    assert len(state_data.get("chapter_summaries", [])) == 0
    assert len(state_data.get("summary_chapter_titles", [])) == 0

    logger.info("Storing adventure state...")
    result = await store_adventure_state(state_data)
    state_id = result.get("state_id")

    logger.info(f"State stored with ID: {state_id}")

    # Retrieve the stored state
    storage_service = StateStorageService()
    stored_state = await storage_service.get_state(state_id)

    # Verify summaries were generated
    assert stored_state is not None
    assert "chapter_summaries" in stored_state
    assert len(stored_state["chapter_summaries"]) == 3  # Should have 3 summaries
    assert "summary_chapter_titles" in stored_state
    assert len(stored_state["summary_chapter_titles"]) == 3  # Should have 3 titles

    # Verify the CONCLUSION chapter has a summary
    conclusion_summary = stored_state["chapter_summaries"][2]
    logger.info(f"CONCLUSION chapter summary: {conclusion_summary[:100]}...")
    assert conclusion_summary, "CONCLUSION chapter should have a summary"

    # Note: We're not testing the full get_adventure_summary functionality here
    # as it requires a valid AdventureState object, which our test state might not fully satisfy.
    # Instead, we're focusing on verifying that the summaries are generated and stored correctly.

    # Log the chapter summaries for verification
    for i, summary in enumerate(stored_state["chapter_summaries"]):
        logger.info(f"Chapter {i + 1} summary: {summary[:50]}...")

    # Log the chapter titles for verification
    for i, title in enumerate(stored_state["summary_chapter_titles"]):
        logger.info(f"Chapter {i + 1} title: {title}")

    logger.info(
        "Test passed! All chapter summaries were properly generated and stored."
    )
    return True


if __name__ == "__main__":
    logger.info("Running test_chapter_summary_fix.py")
    asyncio.run(test_store_adventure_state())
