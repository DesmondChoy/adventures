"""
Helper classes and utility functions for the summary service.
"""

from app.models.story import ChapterType


class ChapterTypeHelper:
    """Helper class for consistent chapter type handling."""

    @staticmethod
    def get_chapter_type_string(chapter_type) -> str:
        """Convert any chapter type representation to a consistent string."""
        if isinstance(chapter_type, ChapterType):
            return chapter_type.value.lower()
        elif isinstance(chapter_type, str):
            return chapter_type.lower()
        elif hasattr(chapter_type, "value"):
            return chapter_type.value.lower()
        elif hasattr(chapter_type, "name"):
            return chapter_type.name.lower()
        else:
            return str(chapter_type).lower()

    @staticmethod
    def is_chapter_type(chapter_type, target_type: ChapterType) -> bool:
        """Check if a chapter type matches the target type."""
        type_str = ChapterTypeHelper.get_chapter_type_string(chapter_type)
        return type_str == target_type.value.lower()

    @staticmethod
    def is_lesson_chapter(chapter_type) -> bool:
        """Check if a chapter is a LESSON chapter."""
        return ChapterTypeHelper.is_chapter_type(chapter_type, ChapterType.LESSON)

    @staticmethod
    def is_conclusion_chapter(chapter_type) -> bool:
        """Check if a chapter is a CONCLUSION chapter."""
        return ChapterTypeHelper.is_chapter_type(chapter_type, ChapterType.CONCLUSION)