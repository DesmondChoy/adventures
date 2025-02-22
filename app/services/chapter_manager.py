from typing import List, Dict, Any
import random
import logging
import math
import yaml
from app.models.story import ChapterType, AdventureState

logger = logging.getLogger("story_app")


def load_story_data() -> Dict[str, Any]:
    """Load story data from new_stories.yaml."""
    try:
        with open("app/data/new_stories.yaml", "r") as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error("Failed to load story data", extra={"error": str(e)})
        raise ValueError(f"Failed to load story data: {str(e)}")


def select_random_elements(
    story_data: Dict[str, Any], story_category: str
) -> Dict[str, Any]:
    """Select random elements from each category for the story.

    Args:
        story_data: The loaded story data
        story_category: The selected story category

    Returns:
        Dict containing randomly selected elements for each category
    """
    categories = story_data.get("story_categories", {})
    if story_category not in categories:
        raise ValueError(f"Invalid story category: {story_category}")

    category_data = categories[story_category]

    logger.info(
        "Selecting random story elements",
        extra={
            "story_category": story_category,
            "available_categories": list(category_data.keys()),
        },
    )

    # Select one random element from each narrative_elements subcategory
    narrative_elements = {
        key: random.choice(values)
        for key, values in category_data["narrative_elements"].items()
        if isinstance(values, list)
    }

    # Select one random element from each sensory_details subcategory
    sensory_details = {
        key: random.choice(values)
        for key, values in category_data["sensory_details"].items()
        if isinstance(values, list)
    }

    # Select one random theme and moral lesson
    selected_theme = random.choice(category_data["narrative_elements"]["themes"])
    selected_moral_lesson = random.choice(
        category_data["narrative_elements"]["moral_lessons"]
    )
    selected_plot_twist = random.choice(
        category_data["narrative_elements"]["plot_twists"]
    )

    logger.debug(
        "Selected story elements",
        extra={
            "narrative_elements": narrative_elements,
            "sensory_details": sensory_details,
            "theme": selected_theme,
            "moral_lesson": selected_moral_lesson,
            "plot_twist": selected_plot_twist,
        },
    )

    return {
        "selected_narrative_elements": narrative_elements,
        "selected_sensory_details": sensory_details,
        "selected_theme": selected_theme,
        "selected_moral_lesson": selected_moral_lesson,
        "selected_plot_twist": selected_plot_twist,
    }


class ChapterManager:
    """Service class for managing chapter progression and type determination."""

    @staticmethod
    def determine_story_phase(current_chapter_number: int, story_length: int) -> str:
        """Determine the current story phase (Journey Quest) based on chapter number and story length.

        Args:
            current_chapter_number: The current chapter number (1-based)
            story_length: Total number of chapters in the story

        Returns:
            str: One of "Exposition", "Rising", "Trials", "Climax", or "Return"
        """
        if current_chapter_number == 1:
            return "Exposition"
        elif current_chapter_number == story_length:
            return "Return"
        else:
            rising_end = math.ceil(story_length * 0.25)
            climax_start = story_length - math.floor(story_length * 0.25)

            if current_chapter_number <= rising_end:
                return "Rising"
            elif current_chapter_number >= climax_start:
                return "Climax"
            else:
                return "Trials"

    @staticmethod
    def determine_chapter_types(
        total_chapters: int, available_questions: int
    ) -> List[ChapterType]:
        """Determine the sequence of chapter types for the entire adventure.

        Args:
            total_chapters: Total number of chapters in the adventure
            available_questions: Number of available questions in the database for the topic

        Returns:
            List of ChapterType values representing the type of each chapter

        Raises:
            ValueError: If there aren't enough questions for the required lessons
        """
        if total_chapters < 4:
            raise ValueError(
                "Total chapters must be at least 4 to accommodate the required chapter types"
            )

        logger.info(
            "Starting chapter type determination",
            extra={
                "total_chapters": total_chapters,
                "available_questions": available_questions,
            },
        )

        # Initialize with all chapters as STORY type
        chapter_types = [ChapterType.STORY] * total_chapters

        # First two chapters are always STORY
        chapter_types[0] = ChapterType.STORY
        chapter_types[1] = ChapterType.STORY

        # Second-to-last chapter is always STORY
        chapter_types[-2] = ChapterType.STORY

        # Last chapter is always CONCLUSION
        chapter_types[-1] = ChapterType.CONCLUSION

        logger.debug(
            "Set mandatory chapter types",
            extra={
                "first_chapter": "STORY",
                "second_chapter": "STORY",
                "second_to_last": "STORY",
                "last_chapter": "CONCLUSION",
                "initial_state": [ct.value for ct in chapter_types],
            },
        )

        # Calculate required number of LESSON chapters (50% of non-conclusion chapters)
        required_lessons = (total_chapters - 1) // 2
        possible_lessons = min(required_lessons, available_questions)

        if possible_lessons < 0:
            error_msg = f"Need at least {required_lessons} questions, but only have {available_questions}"
            logger.error(error_msg, extra={"error_type": "insufficient_questions"})
            raise ValueError(error_msg)

        logger.info(
            "Calculated lesson allocation constraints",
            extra={
                "required_lessons": required_lessons,
                "available_questions": available_questions,
                "possible_lessons": possible_lessons,
            },
        )

        # Get available positions for lessons (excluding first two, second-to-last, and last chapters)
        available_positions = list(range(2, total_chapters - 2))

        # Only attempt to select lesson positions if we have both possible lessons and available positions
        if possible_lessons > 0 and available_positions:
            # Ensure we don't try to sample more positions than are available
            possible_lessons = min(possible_lessons, len(available_positions))

            # Randomly select positions for lessons
            lesson_positions = random.sample(available_positions, possible_lessons)

            # Set selected positions to LESSON type
            for pos in lesson_positions:
                chapter_types[pos] = ChapterType.LESSON

            logger.info(
                "Selected lesson positions",
                extra={
                    "available_positions": available_positions,
                    "selected_positions": lesson_positions,
                    "final_chapter_sequence": [ct.value for ct in chapter_types],
                },
            )
        else:
            logger.info(
                "No lesson positions selected",
                extra={
                    "reason": "no_lessons_possible"
                    if possible_lessons == 0
                    else "no_available_positions",
                    "possible_lessons": possible_lessons,
                    "available_positions_count": len(available_positions),
                    "final_chapter_sequence": [ct.value for ct in chapter_types],
                },
            )

        # Add clear debug log showing final chapter sequence
        logger.debug(
            f"Final Chapter Sequence ({total_chapters} total):\n"
            + f"[{', '.join(ct.value for ct in chapter_types)}]",
            extra={
                "total_chapters": total_chapters,
                "chapter_sequence": [ct.value for ct in chapter_types],
            },
        )

        return chapter_types

    @staticmethod
    def count_available_questions(lesson_topic: str) -> int:
        """Count the number of available questions for a given topic.

        Args:
            lesson_topic: The educational topic to count questions for

        Returns:
            Number of available questions for the topic
        """
        from app.init_data import load_lesson_data

        df = load_lesson_data()
        topic_questions = df[df["topic"] == lesson_topic]
        question_count = len(topic_questions)
        logger.info(
            f"Counted available questions for topic",
            extra={"lesson_topic": lesson_topic, "question_count": question_count},
        )
        return question_count

    @staticmethod
    def initialize_adventure_state(
        total_chapters: int, lesson_topic: str, story_category: str
    ) -> AdventureState:
        """Initialize a new adventure state with the determined chapter types and story elements.

        Args:
            total_chapters: Total number of chapters in the adventure
            lesson_topic: The topic of the lessons
            story_category: The selected story category

        Returns:
            Initialized AdventureState object

        Raises:
            ValueError: If story category is invalid or story data cannot be loaded
        """
        logger.info(
            "Initializing adventure state",
            extra={
                "total_chapters": total_chapters,
                "lesson_topic": lesson_topic,
                "story_category": story_category,
            },
        )

        # Load story data and select random elements
        story_data = load_story_data()
        selected_elements = select_random_elements(story_data, story_category)

        # Initialize chapter types
        available_questions = ChapterManager.count_available_questions(lesson_topic)
        chapter_types = ChapterManager.determine_chapter_types(
            total_chapters, available_questions
        )

        # Create and return the adventure state with all selected elements
        state = AdventureState(
            current_chapter_id="start",
            story_length=total_chapters,
            chapters=[],
            planned_chapter_types=chapter_types,
            current_storytelling_phase="Exposition",  # Initial phase is always Exposition
            selected_narrative_elements=selected_elements[
                "selected_narrative_elements"
            ],
            selected_sensory_details=selected_elements["selected_sensory_details"],
            selected_theme=selected_elements["selected_theme"],
            selected_moral_lesson=selected_elements["selected_moral_lesson"],
            selected_plot_twist=selected_elements["selected_plot_twist"],
        )

        logger.info(
            "Adventure state initialized with story elements",
            extra={
                "story_category": story_category,
                "selected_elements": selected_elements,
                "chapter_types": [ct.value for ct in chapter_types],
            },
        )

        return state
