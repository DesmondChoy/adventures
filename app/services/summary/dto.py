"""
Data Transfer Objects for the summary service.
"""

from typing import Dict, Any, List
from app.utils.case_conversion import snake_to_camel_dict


class AdventureSummaryDTO:
    """Data Transfer Object for adventure summaries."""
    
    def __init__(
        self, 
        chapter_summaries: List[Dict[str, Any]],
        educational_questions: List[Dict[str, Any]],
        statistics: Dict[str, Any]
    ):
        self.chapter_summaries = chapter_summaries
        self.educational_questions = educational_questions
        self.statistics = statistics
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "chapter_summaries": self.chapter_summaries,
            "educational_questions": self.educational_questions,
            "statistics": self.statistics
        }
    
    def to_camel_case(self) -> Dict[str, Any]:
        """Convert to camelCase for API responses."""
        return snake_to_camel_dict(self.to_dict())