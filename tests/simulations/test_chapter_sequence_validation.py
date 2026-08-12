"""Tests for planned and actual chapter sequence log parsing."""

from pathlib import Path

from tests.simulations.log_utils import (
    get_chapter_sequence,
    get_final_chapter_sequence,
)


def test_final_chapter_sequence_is_parsed(tmp_path: Path) -> None:
    log_file = tmp_path / "simulation.log"
    log_file.write_text(
        "2026-08-12 - DEBUG - Final Chapter Sequence (3 total): "
        "[STORY, LESSON, CONCLUSION]\n"
    )

    total_chapters, sequence = get_final_chapter_sequence(str(log_file))

    assert total_chapters == 3
    assert sequence == ["STORY", "LESSON", "CONCLUSION"]


def test_actual_sequence_is_not_replaced_by_planned_sequence(tmp_path: Path) -> None:
    log_file = tmp_path / "simulation.log"
    log_file.write_text(
        "2026-08-12 - DEBUG - Final Chapter Sequence (3 total): "
        "[STORY, STORY, CONCLUSION]\n"
        '2026-08-12 - INFO - {"message": "EVENT:CHAPTER_START", '
        '"chapter_type": "story", "chapter_number": 1}\n'
        '2026-08-12 - INFO - {"message": "EVENT:CHAPTER_START", '
        '"chapter_type": "lesson", "chapter_number": 2}\n'
        '2026-08-12 - INFO - {"message": "EVENT:CHAPTER_START", '
        '"chapter_type": "conclusion", "chapter_number": 3}\n'
    )

    assert get_chapter_sequence(str(log_file)) == [
        "STORY",
        "LESSON",
        "CONCLUSION",
    ]
