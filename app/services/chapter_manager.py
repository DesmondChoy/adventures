from typing import List
import random
import logging
from app.models.story import ChapterType, AdventureState
from app.init_data import sample_question

logger = logging.getLogger("story_app")


class ChapterManager:
    """Service class for managing chapter progression and type determination."""

    # Maximum ratio of lessons to total chapters (excluding mandatory first/last lessons)
    # For example, 0.4 means at most 40% of middle chapters can be lessons
    MAX_LESSON_RATIO = 0.4

    @staticmethod
    def determine_chapter_types(
        total_chapters: int, available_questions: int
    ) -> List[ChapterType]:
        """Determine the sequence of chapter types for the entire adventure up front.

        Args:
            total_chapters: Total number of chapters in the adventure
            available_questions: Number of available questions in the database for the topic

        Returns:
            List of ChapterType values representing the type of each chapter

        Raises:
            ValueError: If there aren't enough questions for the required lessons
        """
        logger.info(
            "Starting chapter type determination",
            extra={
                "total_chapters": total_chapters,
                "available_questions": available_questions,
                "max_lesson_ratio": ChapterManager.MAX_LESSON_RATIO,
            },
        )

        # First and last chapters must be lessons, so we need at least 2 questions
        if available_questions < 2:
            error_msg = (
                f"Need at least 2 questions, but only have {available_questions}"
            )
            logger.error(error_msg, extra={"error_type": "insufficient_questions"})
            raise ValueError(error_msg)

        # Initialize with all chapters as STORY type
        chapter_types = [ChapterType.STORY] * total_chapters

        # First and last chapters are always lessons
        chapter_types[0] = ChapterType.LESSON
        chapter_types[-1] = ChapterType.LESSON

        logger.debug(
            "Set mandatory lesson chapters",
            extra={
                "first_chapter": "LESSON",
                "last_chapter": "LESSON",
                "initial_state": [ct.value for ct in chapter_types],
            },
        )

        # Calculate maximum allowed lessons for middle chapters based on ratio
        middle_chapters = total_chapters - 2  # subtract first and last chapters
        max_middle_lessons = int(middle_chapters * ChapterManager.MAX_LESSON_RATIO)

        # Calculate how many more lesson chapters we can actually add
        remaining_questions = available_questions - 2  # subtract first and last lessons
        possible_additional_lessons = min(remaining_questions, max_middle_lessons)

        logger.info(
            "Calculated lesson allocation constraints",
            extra={
                "middle_chapters": middle_chapters,
                "max_middle_lessons": max_middle_lessons,
                "remaining_questions": remaining_questions,
                "possible_additional_lessons": possible_additional_lessons,
            },
        )

        if possible_additional_lessons > 0:
            # Get positions for potential additional lessons (excluding first and last positions)
            available_positions = list(range(1, total_chapters - 1))
            # Randomly select positions for additional lessons, limited by ratio
            lesson_positions = random.sample(
                available_positions, possible_additional_lessons
            )

            # Set selected positions to LESSON type
            for pos in lesson_positions:
                chapter_types[pos] = ChapterType.LESSON

            logger.info(
                "Selected additional lesson positions",
                extra={
                    "available_positions": available_positions,
                    "selected_positions": lesson_positions,
                    "final_chapter_sequence": [ct.value for ct in chapter_types],
                },
            )
        else:
            logger.info(
                "No additional lesson positions selected",
                extra={
                    "reason": "no_additional_lessons_possible",
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
        total_chapters: int, lesson_topic: str
    ) -> AdventureState:
        """Initialize a new adventure state with the determined chapter types.

        Args:
            total_chapters: Total number of chapters in the adventure
            lesson_topic: The topic of the lessons

        Returns:
            Initialized AdventureState object
        """
        logger.info(
            "Initializing adventure state",
            extra={
                "total_chapters": total_chapters,
                "lesson_topic": lesson_topic,
            },
        )
        available_questions = ChapterManager.count_available_questions(lesson_topic)
        chapter_types = ChapterManager.determine_chapter_types(
            total_chapters, available_questions
        )
        return AdventureState(
            current_chapter_id="start",
            story_length=total_chapters,
            chapters=[],
            planned_chapter_types=chapter_types,
        )
