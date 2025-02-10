from typing import List
import random
import logging
from app.models.story import ChapterType, AdventureState
from app.init_data import sample_question

logger = logging.getLogger("story_app")

class ChapterManager:
    """Service class for managing chapter progression and type determination."""
    
    @staticmethod
    def determine_chapter_types(total_chapters: int, available_questions: int) -> List[ChapterType]:
        """Determine the sequence of chapter types for the entire adventure up front.
        
        Args:
            total_chapters: Total number of chapters in the adventure
            available_questions: Number of available questions in the database for the topic
            
        Returns:
            List of ChapterType values representing the type of each chapter
            
        Raises:
            ValueError: If there aren't enough questions for the required lessons
        """
        # First and last chapters must be lessons, so we need at least 2 questions
        if available_questions < 2:
            raise ValueError(f"Need at least 2 questions, but only have {available_questions}")
            
        # Initialize with all chapters as STORY type
        chapter_types = [ChapterType.STORY] * total_chapters
        
        # First and last chapters are always lessons
        chapter_types[0] = ChapterType.LESSON
        chapter_types[-1] = ChapterType.LESSON
        
        # Calculate how many more lesson chapters we can add
        remaining_questions = available_questions - 2  # subtract first and last lessons
        if remaining_questions > 0:
            # Get positions for potential additional lessons (excluding first and last positions)
            available_positions = list(range(1, total_chapters - 1))
            # Randomly select positions for additional lessons, up to the number of remaining questions
            num_additional_lessons = min(remaining_questions, len(available_positions))
            lesson_positions = random.sample(available_positions, num_additional_lessons)
            
            # Set selected positions to LESSON type
            for pos in lesson_positions:
                chapter_types[pos] = ChapterType.LESSON
                
        return chapter_types
    
    @staticmethod
    def count_available_questions(lesson_topic: str) -> int:
        """Count the number of available questions for a given topic.
        
        Args:
            lesson_topic: The educational topic to count questions for
            
        Returns:
            Number of available questions for the topic
        """
        return len(sample_question(lesson_topic, exclude_questions=[]))
    
    @staticmethod
    def initialize_adventure_state(total_chapters: int, chapter_types: List[ChapterType]) -> AdventureState:
        """Initialize a new adventure state with the determined chapter types.
        
        Args:
            total_chapters: Total number of chapters in the adventure
            chapter_types: Pre-determined sequence of chapter types
            
        Returns:
            Initialized AdventureState object
        """
        return AdventureState(
            current_chapter_id="start",
            story_length=total_chapters,
            chapters=[]
        ) 