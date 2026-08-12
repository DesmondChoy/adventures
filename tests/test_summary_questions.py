"""Regression tests for summary question and chapter processors."""

from typing import Any

from app.models.story import (
    AdventureState,
    ChapterContent,
    ChapterData,
    ChapterType,
    LessonResponse,
    StoryChoice,
)
from app.services.summary.chapter_processor import ChapterProcessor
from app.services.summary.question_processor import QuestionProcessor


def _chapter(
    number: int,
    chapter_type: ChapterType,
    *,
    content: str | None = None,
    question: dict[str, Any] | None = None,
    response: LessonResponse | None = None,
) -> ChapterData:
    chapter_content = content or f"Chapter {number} content"
    choices = (
        [
            StoryChoice(text=f"Choice {index}", next_chapter=f"path-{index}")
            for index in range(1, 4)
        ]
        if chapter_type == ChapterType.STORY
        else []
    )
    return ChapterData(
        chapter_number=number,
        content=chapter_content,
        chapter_type=chapter_type,
        chapter_content=ChapterContent(content=chapter_content, choices=choices),
        question=question,
        response=response,
    )


def test_questions_prefer_state_lesson_questions() -> None:
    state = AdventureState(
        current_chapter_id="chapter-1",
        chapters=[_chapter(1, ChapterType.LESSON)],
        lesson_questions=[
            {
                "question": "Which material conducts electricity?",
                "chosen_answer": "Copper",
                "is_correct": True,
                "explanation": "Copper contains mobile electrons.",
            }
        ],
    )

    questions = QuestionProcessor.extract_educational_questions(state)

    assert questions == [
        {
            "question": "Which material conducts electricity?",
            "user_answer": "Copper",
            "is_correct": True,
            "explanation": "Copper contains mobile electrons.",
        }
    ]


def test_questions_fall_back_to_lesson_chapters() -> None:
    question = {
        "question": "What does a habitat provide?",
        "answers": [
            {"text": "Food and shelter", "is_correct": True},
            {"text": "Only sunlight", "is_correct": False},
        ],
        "explanation": "Habitats meet an organism's needs.",
    }
    response = LessonResponse(
        question=question,
        chosen_answer="Only sunlight",
        is_correct=False,
    )
    state = AdventureState(
        current_chapter_id="chapter-1",
        chapters=[
            _chapter(
                1,
                ChapterType.LESSON,
                question=question,
                response=response,
            )
        ],
    )

    questions = QuestionProcessor.extract_educational_questions(state)

    assert questions[0]["user_answer"] == "Only sunlight"
    assert questions[0]["is_correct"] is False
    assert questions[0]["correct_answer"] == "Food and shelter"


def test_questions_supply_reflection_when_no_lessons_exist() -> None:
    state = AdventureState(
        current_chapter_id="chapter-1",
        chapters=[_chapter(1, ChapterType.CONCLUSION)],
    )

    questions = QuestionProcessor.extract_educational_questions(state)

    assert len(questions) == 1
    assert questions[0]["question"] == "Did you enjoy your adventure?"


def test_chapter_summaries_use_stored_values_and_content_fallbacks() -> None:
    state = AdventureState(
        current_chapter_id="chapter-2",
        story_length=2,
        chapters=[
            _chapter(1, ChapterType.STORY, content="The explorer enters a cave."),
            _chapter(2, ChapterType.CONCLUSION, content="The explorer returns home."),
        ],
        chapter_summaries=["A mysterious cave appears."],
        summary_chapter_titles=["Into the Cave"],
    )

    summaries = ChapterProcessor.extract_chapter_summaries(state)

    assert summaries[0] == {
        "number": 1,
        "title": "Into the Cave",
        "summary": "A mysterious cave appears.",
        "chapter_type": "story",
    }
    assert summaries[1]["summary"] == "The explorer returns home."
    assert summaries[1]["chapter_type"] == "conclusion"


def test_summary_chapters_are_excluded_from_memory_lane() -> None:
    state = AdventureState(
        current_chapter_id="summary",
        story_length=1,
        chapters=[
            _chapter(1, ChapterType.CONCLUSION),
            _chapter(2, ChapterType.SUMMARY),
        ],
    )

    summaries = ChapterProcessor.extract_chapter_summaries(state)

    assert [summary["number"] for summary in summaries] == [1]
