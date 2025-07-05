from typing import List, Dict, Any
import random
import logging
import math
import re
import json
from datetime import datetime
from app.models.story import ChapterType, AdventureState, ChapterData, ChapterContent
from app.data.story_loader import StoryLoader
from app.services.llm import LLMService
from app.services.llm.prompt_templates import (
    SUMMARY_CHAPTER_PROMPT,
    IMAGE_SCENE_PROMPT,
    PREDEFINED_PROTAGONIST_DESCRIPTIONS,
)

logger = logging.getLogger("story_app")


def load_story_data() -> Dict[str, Any]:
    """Load story data from individual YAML files in the stories directory."""
    try:
        loader = StoryLoader()
        return loader.load_all_stories()
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
    required_categories = {"settings"}
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

        Implementation of the new algorithm:
        - Fixed length of 10 chapters
        - Chapters 1 and 9 are STORY
        - Chapter 10 is CONCLUSION
        - Places a LESSON-REFLECT-STORY sequence at a random position between 2-7
        - Selects two non-consecutive positions for additional LESSON chapters
        - Fills remaining positions with STORY

        Args:
            total_chapters: Total number of chapters in the adventure (assumed to be 10)
            available_questions: Number of available questions (assumed to be 3)

        Returns:
            List of ChapterType values representing the type of each chapter

        Raises:
            ValueError: If there aren't enough questions for the required lessons
        """
        # For now, we assume a fixed length of 10 chapters
        if total_chapters != 10:
            logger.warning(
                "This implementation assumes exactly 10 chapters. Using 10 chapters instead of the provided value.",
                extra={"requested_chapters": total_chapters, "using_chapters": 10},
            )
            total_chapters = 10

        # For now, we assume 3 questions available
        if available_questions < 3:
            error_msg = (
                f"Need at least 3 questions, but only have {available_questions}"
            )
            logger.error(error_msg, extra={"error_type": "insufficient_questions"})
            raise ValueError(error_msg)

        logger.info(
            "Starting chapter type determination with new algorithm",
            extra={
                "total_chapters": total_chapters,
                "available_questions": available_questions,
            },
        )

        # Initialize chapters (1-based indexing in algorithm, 0-based in our implementation)
        # We'll create a temporary list with None values, then convert to ChapterType
        chapters = [None] * 10  # 0-9 indices (we'll ignore index 0 for clarity)

        # Set fixed positions
        chapters[0] = "STORY"  # Chapter 1
        chapters[8] = "STORY"  # Chapter 9
        chapters[9] = "CONCLUSION"  # Chapter 10

        logger.debug(
            "Set mandatory chapter types",
            extra={
                "chapter_1": "STORY",
                "chapter_9": "STORY",
                "chapter_10": "CONCLUSION",
            },
        )

        # Randomly choose position for LESSON-REFLECT pair
        i = random.randint(1, 6)  # Position 2-7 (0-indexed: 1-6)

        logger.debug(
            "Selected position for LESSON-REFLECT-STORY sequence",
            extra={"position": i + 1},  # Log 1-indexed position for clarity
        )

        if i <= 5:  # Position 2-6 (0-indexed: 1-5)
            # Place LESSON-REFLECT-STORY sequence
            chapters[i] = "LESSON"
            chapters[i + 1] = "REFLECT"
            chapters[i + 2] = "STORY"
            set_positions = {i, i + 1, i + 2}
            # Exclude position before i to avoid adjacent LESSONs
            exclude = {i - 1} if i - 1 >= 1 else set()
            available = [
                p for p in range(1, 8) if p not in set_positions and p not in exclude
            ]
        else:  # i = 6 (Position 7, 0-indexed: 6)
            # Place LESSON-REFLECT, followed by STORY at 9
            chapters[6] = "LESSON"
            chapters[7] = "REFLECT"
            set_positions = {6, 7}
            # Exclude 5 since 6 is LESSON
            available = [p for p in range(1, 5)]  # 1 to 4

        logger.debug(
            "Placed LESSON-REFLECT-STORY sequence",
            extra={
                "sequence_positions": list(set_positions),
                "available_positions": available,
            },
        )

        # Select two non-consecutive positions for remaining LESSONs
        possible_pairs = []
        for j in range(len(available)):
            for k in range(j + 1, len(available)):
                if available[k] - available[j] > 1:
                    possible_pairs.append((available[j], available[k]))

        if possible_pairs:
            lesson_pair = random.choice(possible_pairs)
            chapters[lesson_pair[0]] = "LESSON"
            chapters[lesson_pair[1]] = "LESSON"

            logger.debug(
                "Selected positions for additional LESSON chapters",
                extra={"lesson_positions": lesson_pair},
            )
        else:
            logger.warning(
                "Could not find non-consecutive positions for additional LESSON chapters",
                extra={"available_positions": available},
            )

        # Fill remaining positions with STORY
        for p in range(1, 9):
            if chapters[p] is None:
                chapters[p] = "STORY"

        # Convert string chapter types to ChapterType enum
        chapter_types = []
        for chapter_type in chapters[0:10]:  # Skip the unused 0 index
            if chapter_type == "STORY":
                chapter_types.append(ChapterType.STORY)
            elif chapter_type == "LESSON":
                chapter_types.append(ChapterType.LESSON)
            elif chapter_type == "REFLECT":
                chapter_types.append(ChapterType.REFLECT)
            elif chapter_type == "CONCLUSION":
                chapter_types.append(ChapterType.CONCLUSION)
            elif chapter_type == "SUMMARY":
                chapter_types.append(ChapterType.SUMMARY)

        # Validate the sequence
        is_valid = ChapterManager.check_chapter_sequence(chapter_types)
        if not is_valid:
            logger.warning(
                "Generated chapter sequence does not pass validation",
                extra={"chapter_sequence": [ct.value.upper() for ct in chapter_types]},
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
    def check_chapter_sequence(chapter_types: List[ChapterType]) -> bool:
        """Validate that the chapter sequence follows the required rules.

        Priority Rules:
        1. No consecutive LESSON chapters (highest priority)
        2. At least 1 REFLECT chapter in every scenario (required)
        3. Every LESSON assumes at least 3 questions available
        4. Accept 25% of scenarios where there are two LESSON chapters (optimization tradeoff)

        Additional Rules:
        - Chapters 1 and 9 are STORY
        - Chapter 10 is CONCLUSION
        - REFLECT chapters must be preceded by LESSON and followed by STORY
        - At least 2 LESSON chapters

        Args:
            chapter_types: List of ChapterType values to validate

        Returns:
            True if the sequence is valid, False otherwise
        """
        # Convert ChapterType enum to strings for easier validation
        seq = [ct.value.upper() for ct in chapter_types]

        # Priority Rule 1: Check no consecutive LESSONs (highest priority)
        for i in range(len(seq) - 1):
            if seq[i] == "LESSON" and seq[i + 1] == "LESSON":
                logger.warning(
                    "Consecutive LESSON check failed (highest priority rule)",
                    extra={"position": i + 1},
                )
                return False

        # Priority Rule 2: Check at least one REFLECT chapter (required)
        if "REFLECT" not in seq:
            logger.warning("No REFLECT chapter found (required rule)")
            return False

        # Check fixed positions
        if seq[0] != "STORY" or seq[8] != "STORY" or seq[9] != "CONCLUSION":
            logger.warning(
                "Fixed position check failed",
                extra={
                    "chapter_1": seq[0],
                    "chapter_9": seq[8],
                    "chapter_10": seq[9],
                },
            )
            return False

        # SUMMARY chapters can only appear after CONCLUSION
        for i, chapter_type in enumerate(seq):
            if chapter_type == "SUMMARY" and (i == 0 or seq[i - 1] != "CONCLUSION"):
                logger.warning(
                    "SUMMARY chapter placement check failed - must follow CONCLUSION",
                    extra={
                        "position": i + 1,
                        "before": seq[i - 1] if i > 0 else "None",
                    },
                )
                return False

        # Check REFLECT placement: LESSON before, STORY after
        for i in range(1, len(seq) - 1):
            if seq[i] == "REFLECT":
                if seq[i - 1] != "LESSON" or seq[i + 1] != "STORY":
                    logger.warning(
                        "REFLECT placement check failed",
                        extra={
                            "position": i + 1,
                            "before": seq[i - 1],
                            "after": seq[i + 1],
                        },
                    )
                    return False

        # Count LESSONs (expect 3, but accept 2 or 3)
        # Priority Rule 4: Accept 25% of scenarios where there are two LESSON chapters
        num_lessons = seq.count("LESSON")
        if num_lessons < 2:
            logger.warning(
                "Insufficient LESSON chapters",
                extra={"lesson_count": num_lessons},
            )
            return False

        return True

    @staticmethod
    def count_available_questions(lesson_topic: str, difficulty: str = None) -> int:
        """Count the number of available questions for a given topic and difficulty.

        Args:
            lesson_topic: The educational topic to count questions for
            difficulty: Optional difficulty level to filter by

        Returns:
            Number of available questions for the topic and difficulty
        """
        from app.data.lesson_loader import LessonLoader

        loader = LessonLoader()

        if difficulty:
            topic_questions = loader.get_lessons_by_topic_and_difficulty(
                lesson_topic, difficulty
            )

            # If fewer than 3 questions available for the specified difficulty, count all questions
            if len(topic_questions) < 3:
                logger.warning(
                    f"Insufficient questions for topic '{lesson_topic}' with difficulty '{difficulty}'. "
                    f"Counting all difficulties."
                )
                topic_questions = loader.get_lessons_by_topic(lesson_topic)
        else:
            topic_questions = loader.get_lessons_by_topic(lesson_topic)

        question_count = len(topic_questions)
        logger.info(
            f"Counted available questions for topic",
            extra={
                "lesson_topic": lesson_topic,
                "difficulty": difficulty,
                "question_count": question_count,
            },
        )
        return question_count

    @staticmethod
    def create_summary_chapter(state: AdventureState) -> ChapterData:
        """Create a summary chapter that follows the CONCLUSION chapter.

        This method creates a new ChapterData object with the SUMMARY chapter type.
        The summary chapter should only be created after the CONCLUSION chapter.

        Args:
            state: The current adventure state

        Returns:
            A new ChapterData object with the SUMMARY chapter type

        Raises:
            ValueError: If the last chapter is not a CONCLUSION chapter
        """
        # Verify that the last chapter is a CONCLUSION chapter
        if (
            not state.chapters
            or state.chapters[-1].chapter_type != ChapterType.CONCLUSION
        ):
            raise ValueError(
                "Summary chapter can only be created after a CONCLUSION chapter"
            )

        # Create a new chapter number (one more than the last chapter)
        new_chapter_number = len(state.chapters) + 1

        # Create an empty ChapterContent with no choices
        chapter_content = ChapterContent(
            content="",  # Will be filled by the LLM service
            choices=[],  # No choices for summary chapter
        )

        # Create the new chapter data
        summary_chapter = ChapterData(
            chapter_number=new_chapter_number,
            content="",  # Will be filled by the LLM service
            chapter_type=ChapterType.SUMMARY,
            response=None,
            chapter_content=chapter_content,
            question=None,
        )

        logger.info(
            f"Created SUMMARY chapter {new_chapter_number}",
            extra={"chapter_number": new_chapter_number},
        )

        return summary_chapter

    @staticmethod
    def initialize_adventure_state(
        total_chapters: int,
        lesson_topic: str,
        story_category: str,
        difficulty: str = None,
    ) -> AdventureState:
        """Initialize a new adventure state with the determined chapter types and story elements.

        Args:
            total_chapters: Total number of chapters in the adventure
            lesson_topic: The topic of the lessons
            story_category: The selected story category
            difficulty: Optional difficulty level for lessons ("Reasonably Challenging" or "Very Challenging")

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
                    "difficulty": difficulty,
                },
            )

            # Load story data and select elements with validation
            story_data = load_story_data()
            selected_elements = select_random_elements(story_data, story_category)

            # Initialize chapter types
            available_questions = ChapterManager.count_available_questions(
                lesson_topic, difficulty
            )
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

            # Randomly select a protagonist description
            selected_protagonist_desc = random.choice(
                PREDEFINED_PROTAGONIST_DESCRIPTIONS
            )

            logger.info(
                f"Selected protagonist description: {selected_protagonist_desc}"
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
                protagonist_description=selected_protagonist_desc,
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

    @staticmethod
    async def generate_image_scene(
        chapter_content: str, character_visuals: Dict[str, str]
    ) -> str:
        """Generate a description of the most visually striking moment from the chapter.

        Args:
            chapter_content: The full text of the chapter (current chapter being displayed)
            character_visuals: Dictionary of current character visual descriptions

        Returns:
            A vivid description (approx 100 words) of the most visually striking moment
            from the chapter, suitable for image generation
        """
        try:
            # Use the LLM service to generate an image scene
            llm = LLMService()

            # Format character visuals as a JSON string for the prompt
            character_visual_context = json.dumps(character_visuals, indent=2)

            # Create a custom prompt for the image scene using the template
            custom_prompt = IMAGE_SCENE_PROMPT.format(
                chapter_content=chapter_content,
                character_visual_context=character_visual_context,
            )
            logger.info("\n" + "=" * 50)
            logger.info("IMAGE_SCENE_PROMPT SENT TO LLM:")
            logger.info(f"{custom_prompt}")
            logger.info("=" * 50 + "\n")

            # We need to override the prompt engineering system
            # Create a minimal AdventureState-like object with just what we need
            class MinimalState:
                def __init__(self):
                    self.current_chapter_id = "image_scene"
                    self.story_length = 1
                    self.chapters = []
                    self.metadata = {"prompt_override": True}

            # Check if we're using Gemini or OpenAI
            is_gemini = (
                isinstance(llm, LLMService) or "Gemini" in llm.__class__.__name__
            )
            logger.debug(f"Using LLM service for image scene: {llm.__class__.__name__}")

            # For Gemini, use the LLM service instead of direct calls
            if is_gemini:
                try:
                    # Use the LLM service for consistent API handling
                    raw_scene = await llm.generate_character_visuals_json(custom_prompt)
                    logger.debug(
                        f"Direct Gemini response for image scene: '{raw_scene}'"
                    )
                except Exception as e:
                    logger.error(
                        f"Error with direct Gemini call for image scene: {str(e)}"
                    )
                    # Fallback to streaming approach
                    chunks = []
                    async for chunk in llm.generate_chapter_stream(
                        story_config={},
                        state=MinimalState(),
                        question=None,
                        previous_lessons=None,
                        context={"prompt_override": custom_prompt},
                    ):
                        chunks.append(chunk)
                    raw_scene = "".join(chunks)
            else:
                # For OpenAI, use the streaming approach
                chunks = []
                async for chunk in llm.generate_chapter_stream(
                    story_config={},
                    state=MinimalState(),
                    question=None,
                    previous_lessons=None,
                    context={"prompt_override": custom_prompt},
                ):
                    chunks.append(chunk)
                raw_scene = "".join(chunks)

            logger.debug(f"Raw collected image scene before strip: '{raw_scene}'")
            logger.debug(f"Raw collected image scene length: {len(raw_scene)}")

            # Strip whitespace
            scene = raw_scene.strip()
            logger.debug(f"Stripped image scene length: {len(scene)}")

            logger.info(f"Generated image scene: '{scene}'")

            # Ensure the scene is not empty - use a more robust check
            if not scene or len(scene) < 5:  # Consider very short scenes as empty too
                logger.warning(
                    f"Generated image scene is empty or too short: '{scene}', using fallback"
                )
                # Use a simple fallback scene based on the first paragraph
                paragraphs = [p for p in chapter_content.split("\n\n") if p.strip()]
                if paragraphs:
                    first_para = paragraphs[0]
                    words = first_para.split()[:20]
                    scene = " ".join(words) + "..."
                    logger.info(f"Using fallback image scene: {scene}")
                else:
                    scene = "A dramatic moment from the story"
                    logger.info("Using generic fallback image scene")

            return scene
        except Exception as e:
            logger.error(f"Error generating image scene: {str(e)}")
            # Return a simplified scene based on the first paragraph
            paragraphs = [p for p in chapter_content.split("\n\n") if p.strip()]
            if paragraphs:
                first_para = paragraphs[0]
                words = first_para.split()[:20]
                return " ".join(words) + "..."
            return "A dramatic moment from the story"

    @staticmethod
    async def generate_chapter_summary(
        chapter_content: str, chosen_choice: str = None, choice_context: str = ""
    ) -> Dict[str, str]:
        """Generate a concise summary of the chapter content.

        Args:
            chapter_content: The full text of the chapter (current chapter being displayed)
            chosen_choice: The text of the choice made at the end of the chapter (if any)
            choice_context: Additional context about the choice (e.g., whether it was correct/incorrect)

        Returns:
            A dictionary containing the title and summary of the chapter

        Note:
            This method is called after each chapter is completed to generate summaries
            that will be displayed in the final summary chapter. These summaries are
            stored in AdventureState.chapter_summaries and the titles in AdventureState.summary_chapter_titles.
        """
        try:
            # Use the LLM service to generate a summary
            llm = LLMService()

            # Create a custom prompt for the chapter summary using the template
            custom_prompt = SUMMARY_CHAPTER_PROMPT.format(
                chapter_content=chapter_content,
                chosen_choice=chosen_choice or "No choice was made",
                choice_context=choice_context,
            )

            # Log the full prompt at INFO level to show in terminal
            logger.info("\n" + "=" * 50)
            logger.info("COMPLETE CHAPTER SUMMARY PROMPT SENT TO LLM:")
            logger.info(f"{custom_prompt}")
            logger.info("=" * 50 + "\n")

            # We need to override the prompt engineering system
            # Create a minimal AdventureState-like object with just what we need
            class MinimalState:
                def __init__(self):
                    self.current_chapter_id = "summary"
                    self.story_length = 1
                    self.chapters = []
                    self.metadata = {"prompt_override": True}

            # Check if we're using Gemini or OpenAI
            is_gemini = (
                isinstance(llm, LLMService) or "Gemini" in llm.__class__.__name__
            )
            logger.debug(f"Using LLM service: {llm.__class__.__name__}")

            # For Gemini, use the LLM service instead of direct calls
            if is_gemini:
                try:
                    # Use the LLM service for consistent API handling
                    raw_summary = await llm.generate_character_visuals_json(custom_prompt)
                    logger.debug(f"Direct Gemini response: '{raw_summary}'")
                except Exception as e:
                    logger.error(f"Error with direct Gemini call: {str(e)}")
                    # Fallback to streaming approach
                    chunks = []
                    async for chunk in llm.generate_chapter_stream(
                        story_config={},
                        state=MinimalState(),
                        question=None,
                        previous_lessons=None,
                        context={"prompt_override": custom_prompt},
                    ):
                        chunks.append(chunk)
                    raw_summary = "".join(chunks)
            else:
                # For OpenAI, use the streaming approach
                chunks = []
                async for chunk in llm.generate_chapter_stream(
                    story_config={},
                    state=MinimalState(),
                    question=None,
                    previous_lessons=None,
                    context={"prompt_override": custom_prompt},
                ):
                    chunks.append(chunk)
                raw_summary = "".join(chunks)

            # logger.debug(f"Raw collected summary before strip: '{raw_summary}'")
            # logger.debug(f"Raw collected summary length: {len(raw_summary)}")

            # Strip whitespace
            summary = raw_summary.strip()
            # logger.debug(f"Stripped summary length: {len(summary)}")

            # logger.info(f"Generated chapter summary: '{summary}'")

            # Parse the response to extract title and summary
            title = ""
            summary_text = ""

            # Split by section headers
            sections = summary.split("# ")

            # Extract title and summary
            for section in sections:
                if section.startswith("CHAPTER TITLE"):
                    title = section.replace("CHAPTER TITLE", "").strip()
                elif section.startswith("CHAPTER SUMMARY"):
                    summary_text = section.replace("CHAPTER SUMMARY", "").strip()

            # If we couldn't extract a title, use a default
            if not title:
                title = f"Chapter Summary"
                logger.warning("Could not extract title from response, using default")

            # If we couldn't extract a summary, use the whole response
            if not summary_text:
                summary_text = summary
                logger.warning(
                    "Could not extract summary from response, using full response"
                )

            # Ensure the summary is not empty - use a more robust check
            if (
                not summary_text or len(summary_text) < 5
            ):  # Consider very short summaries as empty too
                logger.warning(
                    f"Generated summary is empty or too short: '{summary_text}', using fallback"
                )
                # Use a simple fallback summary based on the first paragraph
                paragraphs = [p for p in chapter_content.split("\n\n") if p.strip()]
                if paragraphs:
                    first_para = paragraphs[0]
                    words = first_para.split()[:30]
                    summary_text = " ".join(words) + "..."
                    logger.info(f"Using fallback summary: {summary_text}")
                else:
                    summary_text = "A scene from the story"
                    logger.info("Using generic fallback summary")

                # Also generate a default title if we're using a fallback summary
                if title == "Chapter Summary":
                    title = "Adventure Chapter"

            return {"title": title, "summary": summary_text}
        except Exception as e:
            logger.error(f"Error generating chapter summary: {str(e)}")
            # Return a simplified summary based on the first paragraph
            paragraphs = [p for p in chapter_content.split("\n\n") if p.strip()]
            if paragraphs:
                first_para = paragraphs[0]
                words = first_para.split()[:30]
                return " ".join(words) + "..."
            return "A scene from the story"
