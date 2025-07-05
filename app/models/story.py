from pydantic import BaseModel, Field, field_validator, ValidationInfo
from typing import List, Dict, Any, Optional, Union, Literal
from enum import Enum
import re


class ChapterType(str, Enum):
    """Type of chapter in the adventure."""

    LESSON = "lesson"
    STORY = "story"
    CONCLUSION = "conclusion"
    REFLECT = "reflect"  # New chapter type for deeper understanding after LESSON
    SUMMARY = "summary"  # New chapter type for adventure summary after CONCLUSION


class StoryChoice(BaseModel):
    """Available choice at the end of a story chapter."""

    text: str
    next_chapter: str


class StoryResponse(BaseModel):
    """User's response to a story chapter's choices."""

    chosen_path: str
    choice_text: str


class ChapterContentValidator(BaseModel):
    """Validates and cleans chapter content."""

    content: str

    @field_validator("content")
    @classmethod
    def content_must_not_start_with_chapter(cls, v):
        # Case-insensitive check for any variation of "chapter" at the beginning
        # This handles markdown headings and various formats
        if re.match(r"^(?:#{1,6}\s+)?chapter\b", v, re.IGNORECASE):
            # Automatically fix the content by removing the prefix
            fixed_content = re.sub(
                r"^(?:#{1,6}\s+)?chapter(?:\s+(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten))?:?\s*",
                "",
                v,
                flags=re.IGNORECASE,
            )
            # Ensure the first letter is capitalized after removing the prefix
            if fixed_content:
                fixed_content = fixed_content[0].upper() + fixed_content[1:]
            return fixed_content
        return v


class ChapterContent(BaseModel):
    """Content and available choices for a chapter."""

    content: str
    choices: List[StoryChoice]


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
        if (
            chapter_type in (ChapterType.CONCLUSION, ChapterType.SUMMARY)
            and len(v.choices) != 0
        ):
            raise ValueError(
                f"{chapter_type.value.capitalize()} chapters must have exactly 0 choices"
            )
        return v


class AdventureState(BaseModel):
    """Tracks progression and responses through the educational adventure."""

    current_chapter_id: str
    chapters: List[ChapterData] = []
    story_length: int = Field(default=10)
    planned_chapter_types: List[
        ChapterType
    ] = []  # Pre-determined sequence of chapter types
    current_storytelling_phase: str = (
        "Exposition"  # Current phase in the Journey Quest structure
    )

    # Story elements selected at initialization and maintained throughout the adventure
    selected_narrative_elements: Dict[str, str] = Field(
        default_factory=dict,
        description="One randomly selected element from each narrative_elements category",
    )
    selected_sensory_details: Dict[str, str] = Field(
        default_factory=dict,
        description="One randomly selected element from each sensory_details category",
    )
    selected_theme: str = Field(
        default="",
        description="The selected theme for the adventure",
    )
    selected_moral_teaching: str = Field(
        default="",
        description="The selected moral teaching for the adventure",
    )
    selected_plot_twist: str = Field(
        default="",
        description="The selected plot twist that will develop throughout the adventure",
    )
    protagonist_description: str = Field(
        default="",
        description="Base visual description of the protagonist",
    )
    character_visuals: Dict[str, str] = Field(
        default_factory=dict,
        description="Stores current visual descriptions for characters (protagonist if changed, and NPCs). Key: character name, Value: description."
    )

    # Chapter summaries for the SUMMARY chapter
    chapter_summaries: List[str] = Field(
        default_factory=list,
        description="Summaries of each chapter for display in the SUMMARY chapter",
    )

    # Chapter titles for the SUMMARY chapter
    summary_chapter_titles: List[str] = Field(
        default_factory=list,
        description="Titles of each chapter for display in the SUMMARY chapter",
    )

    # Lesson questions for the SUMMARY chapter
    lesson_questions: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Educational questions encountered during the adventure for display in the SUMMARY chapter",
    )

    # Metadata for element consistency and plot development
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata for tracking element consistency and plot development",
    )

    @field_validator("selected_narrative_elements")
    @classmethod
    def validate_narrative_elements(cls, v: Dict[str, str]) -> Dict[str, str]:
        required_categories = {"settings"}
        if not all(category in v for category in required_categories):
            raise ValueError(
                f"Missing required narrative elements: {required_categories - v.keys()}"
            )
        return v

    @field_validator("selected_sensory_details")
    @classmethod
    def validate_sensory_details(cls, v: Dict[str, str]) -> Dict[str, str]:
        required_categories = {"visuals", "sounds", "smells"}
        if not all(category in v for category in required_categories):
            raise ValueError(
                f"Missing required sensory details: {required_categories - v.keys()}"
            )
        return v

    @field_validator("selected_theme", "selected_moral_teaching", "selected_plot_twist")
    @classmethod
    def validate_non_empty_string(cls, v: str) -> str:
        if not v:
            raise ValueError("Field cannot be empty")
        return v

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
    def validate_chapters(cls, chapters: List[ChapterData], info: ValidationInfo) -> List[ChapterData]:
        if not chapters:
            return chapters

        # Validate chapter sequence
        chapter_numbers = [chapter.chapter_number for chapter in chapters]
        expected_numbers = list(range(1, len(chapters) + 1))

        if chapter_numbers != expected_numbers:
            raise ValueError("Chapter numbers must be sequential starting from 1")

        # Get the actual story_length for this instance (not the default)
        story_length = getattr(info.data, 'story_length', None) if info.data else None
        if story_length is None:
            story_length = cls.model_fields["story_length"].default  # Fallback to default

        # Validate against story_length (allow one extra chapter for SUMMARY)
        max_allowed_chapters = story_length + 1  # +1 for SUMMARY chapter
        if len(chapters) > max_allowed_chapters:
            # Check if the extra chapter is a SUMMARY chapter
            if len(chapters) == story_length + 1:
                last_chapter = chapters[-1]
                if last_chapter.chapter_type != ChapterType.SUMMARY:
                    raise ValueError(
                        f"Chapter {len(chapters)} must be a SUMMARY chapter when exceeding story_length ({story_length})"
                    )
            else:
                raise ValueError(
                    f"Number of chapters cannot exceed story_length + 1 for SUMMARY (max: {max_allowed_chapters}, got: {len(chapters)})"
                )

        return chapters
