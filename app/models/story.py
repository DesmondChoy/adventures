from pydantic import BaseModel, Field, PrivateAttr, field_validator, model_validator, ValidationInfo
from typing import List, Dict, Any, Optional, Union, Callable
from enum import Enum
import re
import asyncio


class ChapterType(str, Enum):
    """Type of chapter in the adventure."""

    LESSON = "lesson"
    STORY = "story"
    CONCLUSION = "conclusion"
    REFLECT = "reflect"
    SUMMARY = "summary"

    @classmethod
    def _missing_(cls, value: object) -> Optional["ChapterType"]:
        if isinstance(value, str):
            normalized = value.strip().lower()
            for member in cls:
                if member.value == normalized:
                    return member
        return None


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
        if re.match(r"^(?:#{1,6}\s+)?chapter\b", v, re.IGNORECASE):
            fixed_content = re.sub(
                r"^(?:#{1,6}\s+)?chapter(?:\s+(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten))?:?\s*",
                "",
                v,
                flags=re.IGNORECASE,
            )
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
    content: str
    chapter_type: ChapterType
    response: Optional[Union[StoryResponse, LessonResponse]] = None
    chapter_content: ChapterContent
    question: Optional[Dict[str, Any]] = None

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
    
    model_config = {"arbitrary_types_allowed": True}

    current_chapter_id: str
    chapters: List[ChapterData] = []
    story_length: int = Field(default=10)
    planned_chapter_types: List[ChapterType] = []
    current_storytelling_phase: str = "Exposition"

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
    protagonist_name: str = Field(
        default="",
        description="Protagonist name selected once for the adventure",
    )
    character_visuals: Dict[str, str] = Field(
        default_factory=dict,
        description="Stores current visual descriptions for characters (protagonist if changed, and NPCs). Key: character name, Value: description.",
    )

    chapter_summaries: List[str] = Field(
        default_factory=list,
        description="Summaries of each chapter for display in the SUMMARY chapter",
    )

    summary_chapter_titles: List[str] = Field(
        default_factory=list,
        description="Titles of each chapter for display in the SUMMARY chapter",
    )

    lesson_questions: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Educational questions encountered during the adventure for display in the SUMMARY chapter",
    )

    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata for tracking element consistency and plot development",
    )

    pending_background_tasks: List[asyncio.Task] = Field(
        default_factory=list,
        description="Running asyncio.Tasks created by factories, awaited before summary reveal",
        exclude=True,
        repr=False,
    )

    deferred_task_factories: List[Callable[[], Any]] = Field(
        default_factory=list,
        description="Factory functions queued during chapter processing, executed after streaming completes",
        exclude=True,
        repr=False,
    )

    _summary_lock: asyncio.Lock = PrivateAttr(default_factory=asyncio.Lock)
    _chapters_lock: asyncio.Lock = PrivateAttr(default_factory=asyncio.Lock)
    _character_visuals_lock: asyncio.Lock = PrivateAttr(default_factory=asyncio.Lock)

    @property
    def summary_lock(self) -> asyncio.Lock:
        """Get the summary lock for serialized summary generation."""
        return self._summary_lock

    @property
    def chapters_lock(self) -> asyncio.Lock:
        """Get the chapters lock for serialized chapter mutations."""
        return self._chapters_lock

    @property
    def character_visuals_lock(self) -> asyncio.Lock:
        """Serialize character-visual extraction and state replacement."""
        return self._character_visuals_lock

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

    @property
    def correct_lesson_answers(self) -> int:
        """Number of correctly answered lesson questions"""
        return sum(
            1
            for chapter in self.chapters
            if chapter.chapter_type == ChapterType.LESSON
            and isinstance(chapter.response, LessonResponse)
            and chapter.response.is_correct
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
            if chapter.chapter_type == ChapterType.STORY
            and isinstance(chapter.response, StoryResponse)
        ]

    @property
    def lesson_responses(self) -> List[LessonResponse]:
        """List of responses to lesson questions"""
        return [
            chapter.response
            for chapter in self.chapters
            if chapter.chapter_type == ChapterType.LESSON
            and isinstance(chapter.response, LessonResponse)
        ]

    @property
    def all_previous_content(self) -> List[str]:
        """Content from all completed chapters"""
        return [chapter.content for chapter in self.chapters]

    @property
    def previous_chapter_content(self) -> Optional[str]:
        """Content from the most recently completed chapter"""
        return self.chapters[-1].content if self.chapters else None

    @model_validator(mode="after")
    def validate_chapters(self) -> "AdventureState":
        if not self.chapters:
            return self

        chapter_numbers = [chapter.chapter_number for chapter in self.chapters]
        expected_numbers = list(range(1, len(self.chapters) + 1))

        if chapter_numbers != expected_numbers:
            raise ValueError("Chapter numbers must be sequential starting from 1")

        max_allowed_chapters = self.story_length + 1
        if len(self.chapters) > max_allowed_chapters:
            raise ValueError(
                f"Number of chapters cannot exceed story_length + 1 for SUMMARY (max: {max_allowed_chapters}, got: {len(self.chapters)})"
            )
        if (
            len(self.chapters) == max_allowed_chapters
            and self.chapters[-1].chapter_type != ChapterType.SUMMARY
        ):
            raise ValueError(
                f"Chapter {len(self.chapters)} must be a SUMMARY chapter when exceeding story_length ({self.story_length})"
            )

        return self
