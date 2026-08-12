"""Deterministic tests for chapter type assignment."""

import random

import pytest

from app.models.story import ChapterType
from app.services.chapter_manager import ChapterManager


@pytest.mark.parametrize("seed", range(50))
def test_chapter_type_assignment_obeys_story_rules(
    seed: int,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rng = random.Random(seed)
    monkeypatch.setattr("app.services.chapter_manager.random.randint", rng.randint)
    monkeypatch.setattr("app.services.chapter_manager.random.choice", rng.choice)

    sequence = ChapterManager.determine_chapter_types(10, available_questions=3)

    assert len(sequence) == 10
    assert sequence[0] == ChapterType.STORY
    assert sequence[8] == ChapterType.STORY
    assert sequence[9] == ChapterType.CONCLUSION
    assert sequence.count(ChapterType.LESSON) == 3
    assert sequence.count(ChapterType.REFLECT) == 1
    assert ChapterManager.check_chapter_sequence(sequence)

    for index, chapter_type in enumerate(sequence):
        if chapter_type == ChapterType.LESSON and index + 1 < len(sequence):
            assert sequence[index + 1] != ChapterType.LESSON
        if chapter_type == ChapterType.REFLECT:
            assert sequence[index - 1] == ChapterType.LESSON
            assert sequence[index + 1] == ChapterType.STORY


def test_chapter_type_assignment_requires_three_questions() -> None:
    with pytest.raises(ValueError, match="Need at least 3 questions"):
        ChapterManager.determine_chapter_types(10, available_questions=2)


def test_chapter_type_assignment_normalizes_story_length() -> None:
    sequence = ChapterManager.determine_chapter_types(7, available_questions=3)

    assert len(sequence) == 10
    assert sequence[-1] == ChapterType.CONCLUSION


def test_sequence_validation_rejects_consecutive_lessons() -> None:
    sequence = [
        ChapterType.STORY,
        ChapterType.LESSON,
        ChapterType.LESSON,
        ChapterType.STORY,
        ChapterType.STORY,
        ChapterType.STORY,
        ChapterType.STORY,
        ChapterType.REFLECT,
        ChapterType.STORY,
        ChapterType.CONCLUSION,
    ]

    assert ChapterManager.check_chapter_sequence(sequence) is False
