from pydantic import BaseModel, Field, field_validator, ValidationInfo
from typing import List, Dict, Any, Optional, Union, Literal
from enum import Enum


class ChapterType(str, Enum):
    """Type of chapter in the adventure."""

    LESSON = "lesson"
    STORY = "story"
    CONCLUSION = "conclusion"


class StoryChoice(BaseModel):
    """Available choice at the end of a story chapter."""

    text: str
    next_chapter: str


class StoryResponse(BaseModel):
    """User's response to a story chapter's choices."""

    chosen_path: str
    choice_text: str


class ChapterContent(BaseModel):
    """Content and available choices for a chapter."""

    content: str
    choices: List[StoryChoice]

    @field_validator("choices", mode="after")
    @classmethod
    def validate_choices(
        cls, v: List[StoryChoice], info: ValidationInfo
    ) -> List[StoryChoice]:
        if info.data.get("chapter_type") == ChapterType.CONCLUSION:
            return v
        if not v:
            raise ValueError("Must have at least one choice")
        return v


class LessonResponse(BaseModel):
    """User's response to a lesson chapter's question."""

    question: Dict[str, Any]
    chosen_answer: str
    is_correct: bool


class ChapterData(BaseModel):
    """A chapter with its content and the user's response."""

    chapter_number: int
    content: str  # Keep this as string, as it represents the raw content
    chapter_type: ChapterType
    response: Optional[Union[StoryResponse, LessonResponse]] = None
    chapter_content: ChapterContent  # Add the ChapterContent object
    question: Optional[Dict[str, Any]] = None  # Store the question for lesson chapters

    @field_validator("chapter_number")
    @classmethod
    def validate_chapter_number(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Chapter number must be positive")
        return v

    @field_validator("chapter_content", mode="after")
    @classmethod
    def validate_chapter_content(
        cls, v: ChapterContent, info: ValidationInfo
    ) -> ChapterContent:
        chapter_type = info.data.get("chapter_type")

        if chapter_type == ChapterType.STORY and len(v.choices) != 3:
            raise ValueError("Story chapters must have exactly 3 choices")
        if chapter_type == ChapterType.CONCLUSION and len(v.choices) != 0:
            raise ValueError("Conclusion chapters must have exactly 0 choices")
        return v


class AdventureState(BaseModel):
    """Tracks progression and responses through the educational adventure."""

    current_chapter_id: str
    chapters: List[ChapterData] = []
    story_length: int = Field(default=5, ge=5, le=10)
    planned_chapter_types: List[
        ChapterType
    ] = []  # Pre-determined sequence of chapter types
    current_storytelling_phase: str = (
        "Exposition"  # Current phase in the Journey Quest structure
    )

    @property
    def current_chapter_number(self) -> int:
        """Current chapter number (1-based indexing)"""
        return len(self.chapters) + 1

    def _is_lesson_response(self, chapter: ChapterData) -> bool:
        """Helper method to check if chapter has a valid lesson response."""
        return (
            chapter.chapter_type == ChapterType.LESSON
            and chapter.response is not None
            and isinstance(chapter.response, LessonResponse)
        )

    def _is_story_response(self, chapter: ChapterData) -> bool:
        """Helper method to check if chapter has a valid story response."""
        return (
            chapter.chapter_type == ChapterType.STORY
            and chapter.response is not None
            and isinstance(chapter.response, StoryResponse)
        )

    @property
    def correct_lesson_answers(self) -> int:
        """Number of correctly answered lesson questions"""
        return sum(
            1
            for chapter in self.chapters
            if self._is_lesson_response(chapter) and chapter.response.is_correct  # type: ignore[union-attr]
        )

    @property
    def total_lessons(self) -> int:
        """Total number of lesson chapters encountered"""
        return sum(
            1 for chapter in self.chapters if chapter.chapter_type == ChapterType.LESSON
        )

    @property
    def story_choices(self) -> List[StoryResponse]:
        """List of choices made in story chapters"""
        return [
            chapter.response
            for chapter in self.chapters
            if self._is_story_response(chapter)
        ]  # type: ignore[misc]

    @property
    def lesson_responses(self) -> List[LessonResponse]:
        """List of responses to lesson questions"""
        return [
            chapter.response
            for chapter in self.chapters
            if self._is_lesson_response(chapter)
        ]  # type: ignore[misc]

    @property
    def all_previous_content(self) -> List[str]:
        """Content from all completed chapters"""
        return [chapter.content for chapter in self.chapters]

    @property
    def previous_chapter_content(self) -> Optional[str]:
        """Content from the most recently completed chapter"""
        return self.chapters[-1].content if self.chapters else None

    @field_validator("chapters")
    @classmethod
    def validate_chapters(cls, chapters: List[ChapterData]) -> List[ChapterData]:
        if not chapters:
            return chapters

        # Validate chapter sequence
        chapter_numbers = [chapter.chapter_number for chapter in chapters]
        expected_numbers = list(range(1, len(chapters) + 1))

        if chapter_numbers != expected_numbers:
            raise ValueError("Chapter numbers must be sequential starting from 1")

        # Validate against story_length
        if len(chapters) > cls.model_fields["story_length"].default:
            raise ValueError(
                f"Number of chapters cannot exceed story_length ({cls.model_fields['story_length'].default})"
            )

        return chapters
