"""
Statistics processing functionality for calculating adventure statistics.
"""

import logging
from typing import Dict, Any, List

from app.models.story import AdventureState, ChapterType
from app.services.summary.helpers import ChapterTypeHelper

logger = logging.getLogger("summary_service.stats_processor")


class StatsProcessor:
    """Processes adventure statistics."""
    
    @staticmethod
    def calculate_adventure_statistics(state: AdventureState, questions: List[Dict[str, Any]], time_spent: str = None) -> Dict[str, Any]:
        """Calculate adventure statistics with safety checks.

        Args:
            state: The adventure state to process
            questions: List of extracted educational questions

        Returns:
            Dictionary with adventure statistics
        """
        logger.info("\n=== Calculating Adventure Statistics ===")

        # Count chapters by type
        chapter_counts = StatsProcessor._count_chapters_by_type(state)
        logger.info(f"Chapter type counts: {chapter_counts}")

        # Calculate educational statistics
        total_questions, correct_answers = StatsProcessor._calculate_question_stats(questions)
        logger.info(f"Raw statistics: questions={total_questions}, correct={correct_answers}")

        # Ensure at least one question for valid statistics
        if total_questions == 0:
            total_questions = 1
            correct_answers = 1  # Assume correct for better user experience
            logger.info("Adjusted to minimum values: questions=1, correct=1")

        # Count only user-visible chapters (excluding SUMMARY chapters)
        user_chapters = [
            chapter for chapter in state.chapters 
            if chapter.chapter_type != ChapterType.SUMMARY
        ]
        chapters_completed = len(user_chapters)
        
        # Use provided time_spent or calculate fallback estimate
        if time_spent is None:
            estimated_minutes = chapters_completed * 3  # Assume ~3 minutes per chapter
            time_spent = f"{estimated_minutes} mins"

        statistics = {
            "chapters_completed": chapters_completed,
            "questions_answered": total_questions,
            "time_spent": time_spent,
            "correct_answers": correct_answers,
        }

        logger.info(f"Final statistics: {statistics}")
        return statistics
    
    @staticmethod
    def _count_chapters_by_type(state: AdventureState) -> Dict[str, int]:
        """Count the number of chapters by type."""
        chapter_counts = {}
        for chapter in state.chapters:
            chapter_type = ChapterTypeHelper.get_chapter_type_string(chapter.chapter_type)
            chapter_counts[chapter_type] = chapter_counts.get(chapter_type, 0) + 1
        return chapter_counts
    
    @staticmethod
    def _calculate_question_stats(questions: List[Dict[str, Any]]) -> tuple:
        """Calculate question statistics."""
        total_questions = max(len(questions), 1)  # Avoid division by zero
        correct_answers = sum(1 for q in questions if q.get("is_correct", False))
        
        # Ensure logical values
        correct_answers = min(correct_answers, total_questions)
        
        return total_questions, correct_answers