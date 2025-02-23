from typing import List, Dict, Any
import random
import logging
import math
import yaml
from datetime import datetime
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
    """Select and validate story elements according to the Story Elements Pattern.

    Args:
        story_data: The loaded story data
        story_category: The selected story category

    Returns:
        Dict containing both random and non-random elements structured according to pattern

    Raises:
        ValueError: If required elements are missing or invalid
    """
    categories = story_data.get("story_categories", {})
    if story_category not in categories:
        raise ValueError(f"Invalid story category: {story_category}")

    category_data = categories[story_category]

    # 1. Extract non-random elements (must exist and be non-empty)
    try:
        non_random_elements = {
            "name": category_data["name"],
            "description": category_data["description"],
            "tone": category_data["tone"],
        }
        for key, value in non_random_elements.items():
            if not value or not isinstance(value, str):
                raise ValueError(f"Invalid {key}: must be non-empty string")
    except KeyError as e:
        raise ValueError(f"Missing required non-random element: {e}")

    logger.info(
        "Extracted non-random elements",
        extra={
            "story_category": story_category,
            "non_random_elements": non_random_elements,
        },
    )

    # 2. Select and validate required narrative elements
    required_categories = {"setting_types", "character_archetypes", "story_rules"}
    narrative_elements = {}

    try:
        for key in required_categories:
            elements = category_data.get("narrative_elements", {}).get(key, [])
            if not isinstance(elements, list) or not elements:
                raise ValueError(f"Invalid {key}: must be non-empty list")
            narrative_elements[key] = random.choice(elements)
    except Exception as e:
        raise ValueError(f"Error selecting narrative elements: {str(e)}")

    # 3. Select and validate required sensory details
    required_sensory = {"visuals", "sounds", "smells"}
    sensory_details = {}

    try:
        for key in required_sensory:
            elements = category_data.get("sensory_details", {}).get(key, [])
            if not isinstance(elements, list) or not elements:
                raise ValueError(f"Invalid {key}: must be non-empty list")
            sensory_details[key] = random.choice(elements)
    except Exception as e:
        raise ValueError(f"Error selecting sensory details: {str(e)}")

    # 4. Select theme, moral teaching, and plot twist with validation
    try:
        themes = category_data["narrative_elements"]["themes"]
        moral_teachings = category_data["narrative_elements"]["moral_teachings"]
        plot_twists = category_data["narrative_elements"]["plot_twists"]

        if not all(
            isinstance(x, list) and x for x in [themes, moral_teachings, plot_twists]
        ):
            raise ValueError(
                "themes, moral_teachings, and plot_twists must be non-empty lists"
            )

        selected_theme = random.choice(themes)
        selected_moral_teaching = random.choice(moral_teachings)
        selected_plot_twist = random.choice(plot_twists)
    except Exception as e:
        raise ValueError(f"Error selecting theme/moral/twist: {str(e)}")

    logger.debug(
        "Selected story elements",
        extra={
            "non_random_elements": non_random_elements,
            "narrative_elements": narrative_elements,
            "sensory_details": sensory_details,
            "theme": selected_theme,
            "moral_teaching": selected_moral_teaching,
            "plot_twist": selected_plot_twist,
        },
    )

    # Return structured format according to pattern
    return {
        "non_random_elements": non_random_elements,
        "selected_narrative_elements": narrative_elements,
        "selected_sensory_details": sensory_details,
        "selected_theme": selected_theme,
        "selected_moral_teaching": selected_moral_teaching,
        "selected_plot_twist": selected_plot_twist,
    }


def get_plot_twist_guidance(phase: str, plot_twist: str) -> str:
    """Get phase-specific guidance for plot twist development.

    Args:
        phase: Current story phase
        plot_twist: The selected plot twist

    Returns:
        Guidance string for incorporating plot twist in current phase
    """
    phase_guidance = {
        "Exposition": "Subtle hints and background elements only",
        "Rising": "Begin connecting previous hints, maintain mystery",
        "Trials": "Build tension and increase visibility of hints",
        "Climax": "Full revelation and impact of the twist",
        "Return": "Show aftermath and consequences",
    }

    if phase not in phase_guidance:
        raise ValueError(f"Invalid story phase: {phase}")

    return f"Plot Twist '{plot_twist}' - {phase_guidance[phase]}"


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
            ValueError: If story category is invalid, story data cannot be loaded,
                      or element consistency validation fails
        """
        try:
            logger.info(
                "Initializing adventure state",
                extra={
                    "total_chapters": total_chapters,
                    "lesson_topic": lesson_topic,
                    "story_category": story_category,
                },
            )

            # Load story data and select elements with validation
            story_data = load_story_data()
            selected_elements = select_random_elements(story_data, story_category)

            # Initialize chapter types
            available_questions = ChapterManager.count_available_questions(lesson_topic)
            chapter_types = ChapterManager.determine_chapter_types(
                total_chapters, available_questions
            )

            # Get initial plot twist guidance for Exposition phase
            plot_twist_guidance = get_plot_twist_guidance(
                "Exposition", selected_elements["selected_plot_twist"]
            )

            logger.info(
                "Initial plot twist guidance",
                extra={"phase": "Exposition", "guidance": plot_twist_guidance},
            )

            # Create adventure state with validated elements
            state = AdventureState(
                current_chapter_id="start",
                story_length=total_chapters,
                chapters=[],
                planned_chapter_types=chapter_types,
                current_storytelling_phase="Exposition",
                selected_narrative_elements=selected_elements[
                    "selected_narrative_elements"
                ],
                selected_sensory_details=selected_elements["selected_sensory_details"],
                selected_theme=selected_elements["selected_theme"],
                selected_moral_teaching=selected_elements["selected_moral_teaching"],
                selected_plot_twist=selected_elements["selected_plot_twist"],
            )

            # Store metadata for consistency checks and plot development
            state.metadata = {
                "non_random_elements": selected_elements["non_random_elements"],
                "initial_plot_twist_guidance": plot_twist_guidance,
                "story_category": story_category,
                "initialization_time": datetime.now().isoformat(),
                "element_consistency": {
                    "theme": selected_elements["selected_theme"],
                    "moral_teaching": selected_elements["selected_moral_teaching"],
                    "plot_twist": selected_elements["selected_plot_twist"],
                    "narrative_elements": selected_elements[
                        "selected_narrative_elements"
                    ],
                    "sensory_details": selected_elements["selected_sensory_details"],
                },
            }

            logger.info(
                "Adventure state initialized with validated elements",
                extra={
                    "story_category": story_category,
                    "non_random_elements": selected_elements["non_random_elements"],
                    "chapter_types": [ct.value for ct in chapter_types],
                    "plot_twist_guidance": plot_twist_guidance,
                },
            )

            return state

        except Exception as e:
            error_msg = f"Failed to initialize adventure state: {str(e)}"
            logger.error(
                error_msg,
                extra={
                    "story_category": story_category,
                    "error_type": type(e).__name__,
                },
                exc_info=True,
            )
            raise ValueError(error_msg) from e
