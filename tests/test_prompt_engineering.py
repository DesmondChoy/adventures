import pytest
from app.services.llm.prompt_engineering import process_consequences
from app.models.story import StoryState, ChoiceHistory


def test_process_consequences_with_incorrect_answer():
    # Mock question data
    previous_question = {
        "question": "Which year did Sir Stamford Raffles establish Singapore as a British trading post?",
        "answers": [
            {"text": "1819", "is_correct": True},
            {"text": "1859", "is_correct": False},
            {"text": "1789", "is_correct": False},
        ],
    }

    # Get the consequences text
    consequences = process_consequences(False, previous_question, "1859")

    # Verify the text contains the actual chosen answer (1859) not the wrong answer (1789)
    assert "character answered 1859" in consequences
    assert "1819 was the correct answer" in consequences
    assert "1789" not in consequences


def test_process_consequences_with_correct_answer():
    # Mock question data
    previous_question = {
        "question": "Which year did Sir Stamford Raffles establish Singapore as a British trading post?",
        "answers": [
            {"text": "1819", "is_correct": True},
            {"text": "1859", "is_correct": False},
            {"text": "1789", "is_correct": False},
        ],
    }

    # Get the consequences text
    consequences = process_consequences(True, previous_question, "1819")

    # Verify the text acknowledges the correct answer
    assert "correctly identified 1819" in consequences


def test_process_consequences_with_none_values():
    consequences = process_consequences(None, None, None)
    assert consequences == ""
