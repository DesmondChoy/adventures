from typing import List
import random
import logging
import math
from app.models.story import ChapterType, AdventureState
from app.init_data import sample_question

logger = logging.getLogger("story_app")


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
            middle_chapters = story_length - 2
            rising_chapters = math.ceil(middle_chapters * 0.25)
            climax_chapters = math.ceil(middle_chapters * 0.25)

            if current_chapter_number <= 1 + rising_chapters:
                return "Rising"
            elif current_chapter_number > story_length - 1 - climax_chapters:
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
            current_storytelling_phase="Exposition",  # Initial phase is always Exposition
        )
