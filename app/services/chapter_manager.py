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

        # First chapter is always STORY (changed from first two chapters)
        chapter_types[0] = ChapterType.STORY

        # Second-to-last chapter is always STORY
        chapter_types[-2] = ChapterType.STORY

        # Last chapter is always CONCLUSION
        chapter_types[-1] = ChapterType.CONCLUSION

        logger.debug(
            "Set mandatory chapter types",
            extra={
                "first_chapter": "STORY",
                "second_to_last": "STORY",
                "last_chapter": "CONCLUSION",
                "initial_state": [ct.value.upper() for ct in chapter_types],
            },
        )

        # Calculate required number of LESSON chapters (50% of remaining chapters, rounded down)
        # Remaining chapters = total - 3 (first, second-to-last, and last)
        remaining_chapters = total_chapters - 3
        required_lessons = remaining_chapters // 2
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

        # Get available positions for lessons (excluding first, second-to-last, and last chapters)
        available_positions = list(range(1, total_chapters - 2))

        # Only attempt to select lesson positions if we have both possible lessons and available positions
        if possible_lessons > 0 and available_positions:
            # Ensure we don't try to sample more positions than are available
            possible_lessons = min(possible_lessons, len(available_positions))

            # Randomly select positions for lessons
            lesson_positions = random.sample(available_positions, possible_lessons)
            lesson_positions.sort()  # Sort to ensure sequential processing

            # Set selected positions to LESSON type
            for pos in lesson_positions:
                chapter_types[pos] = ChapterType.LESSON

            logger.info(
                "Selected lesson positions",
                extra={
                    "available_positions": available_positions,
                    "selected_positions": lesson_positions,
                },
            )

            # Ensure no consecutive LESSON chapters
            # Iterate through the chapter types and check for consecutive LESSON chapters
            for i in range(1, len(chapter_types)):
                if (
                    chapter_types[i] == ChapterType.LESSON
                    and chapter_types[i - 1] == ChapterType.LESSON
                ):
                    # If we find consecutive LESSON chapters, convert the second one to STORY
                    chapter_types[i] = ChapterType.STORY
                    logger.info(
                        "Converted consecutive LESSON chapter to STORY",
                        extra={"position": i, "previous_position": i - 1},
                    )

            # Get updated positions of LESSON chapters after fixing consecutive ones
            lesson_positions = [
                i for i, ct in enumerate(chapter_types) if ct == ChapterType.LESSON
            ]
            lesson_count = len(lesson_positions)

            # Calculate required number of REASON chapters (50% of LESSON chapters, rounded down)
            required_reasons = lesson_count // 2

            # Only proceed if we need to add REASON chapters
            if required_reasons > 0 and lesson_positions:
                # Randomly select which LESSON chapters will be followed by REASON chapters
                reason_after_positions = random.sample(
                    lesson_positions, required_reasons
                )
                reason_after_positions.sort()  # Sort for sequential processing

                logger.info(
                    "Selected positions for REASON chapters",
                    extra={
                        "lesson_positions": lesson_positions,
                        "reason_after_positions": reason_after_positions,
                    },
                )

                # Create a working copy that can be expanded
                working_sequence = chapter_types.copy()

                # Track insertions to adjust indices
                insertion_count = 0

                # Process from start to end to maintain correct indices
                for original_pos in sorted(reason_after_positions):
                    # Adjust position based on previous insertions
                    adjusted_pos = original_pos + insertion_count

                    # Check if we can insert REASON without disrupting fixed positions
                    # We need to ensure we don't push second-to-last or last chapter out of position
                    if adjusted_pos + 1 < len(working_sequence) - 2:
                        # Insert REASON after LESSON
                        working_sequence.insert(adjusted_pos + 1, ChapterType.REASON)
                        insertion_count += 1

                        # Ensure STORY after REASON
                        if adjusted_pos + 2 < len(working_sequence):
                            working_sequence[adjusted_pos + 2] = ChapterType.STORY

                # Trim back to required length if needed
                if len(working_sequence) > total_chapters:
                    # Identify positions that can be removed (not fixed positions)
                    # We want to preserve: first chapter, second-to-last chapter, last chapter
                    # Also preserve: LESSON chapters, REASON chapters, and STORY chapters after REASON

                    # Calculate how many chapters to remove
                    excess = len(working_sequence) - total_chapters

                    # Find removable STORY chapters (not in fixed positions and not after REASON)
                    removable_positions = []
                    for i in range(1, len(working_sequence) - 2):
                        # Skip the chapter after a REASON chapter (must be STORY)
                        if i > 0 and working_sequence[i - 1] == ChapterType.REASON:
                            continue
                        # Skip LESSON and REASON chapters
                        if working_sequence[i] == ChapterType.STORY:
                            removable_positions.append(i)

                    # If we need to remove more chapters than available removable positions,
                    # we'll need to adjust our strategy (this shouldn't happen with our constraints)
                    if excess > len(removable_positions):
                        logger.warning(
                            "Not enough removable positions to maintain chapter count",
                            extra={
                                "excess_chapters": excess,
                                "removable_positions": len(removable_positions),
                            },
                        )
                        # Fall back to original chapter types
                        working_sequence = chapter_types
                    else:
                        # Remove excess chapters from the end of removable positions list
                        # This prioritizes keeping early STORY chapters
                        positions_to_remove = sorted(
                            removable_positions[-excess:], reverse=True
                        )

                        for pos in positions_to_remove:
                            working_sequence.pop(pos)

                # Update chapter_types with the final sequence
                chapter_types = working_sequence[:total_chapters]
        else:
            logger.info(
                "No lesson positions selected",
                extra={
                    "reason": "no_lessons_possible"
                    if possible_lessons == 0
                    else "no_available_positions",
                    "possible_lessons": possible_lessons,
                    "available_positions_count": len(available_positions),
                },
            )

        # Add clear debug log showing final chapter sequence
        logger.debug(
            f"Final Chapter Sequence ({total_chapters} total):\n"
            + f"[{', '.join(ct.value.upper() for ct in chapter_types)}]",
            extra={
                "total_chapters": total_chapters,
                "chapter_sequence": [ct.value.upper() for ct in chapter_types],
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
                    "chapter_types": [ct.value.upper() for ct in chapter_types],
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
