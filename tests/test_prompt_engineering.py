import pytest
from app.services.llm.prompt_engineering import process_consequences
from app.models.story import StoryState, ChoiceHistory


def test_process_consequences_with_incorrect_answer():
    # Create a state with a history entry
    state = StoryState(
        current_node="wrong1",
        depth=2,
        history=[ChoiceHistory(node_id="wrong1", display_text="1859")],
        correct_answers=0,
        total_questions=1,
        previous_content=None,
        question_history=[],
    )

    # Mock question data
    previous_question = {
        "question": "Which year did Sir Stamford Raffles establish Singapore as a British trading post?",
        "correct_answer": "1819",
        "wrong_answer1": "1859",
        "wrong_answer2": "1789",
    }

    # Get the consequences text
    consequences = process_consequences(state, False, previous_question, "1859")

    # Verify the text contains the actual chosen answer (1859) not the wrong_answer2 (1789)
    assert "character answered 1859" in consequences
    assert "1819 was the correct answer" in consequences
    assert (
        "1789" not in consequences
    )  # Make sure the other wrong answer isn't mentioned


def test_process_consequences_with_correct_answer():
    # Create a state with a history entry
    state = StoryState(
        current_node="correct",
        depth=2,
        history=[ChoiceHistory(node_id="correct", display_text="1819")],
        correct_answers=1,
        total_questions=1,
        previous_content=None,
        question_history=[],
    )

    # Mock question data
    previous_question = {
        "question": "Which year did Sir Stamford Raffles establish Singapore as a British trading post?",
        "correct_answer": "1819",
        "wrong_answer1": "1859",
        "wrong_answer2": "1789",
    }

    # Get the consequences text
    consequences = process_consequences(state, True, previous_question, "1819")

    # Verify the text acknowledges the correct answer
    assert "correctly identified 1819" in consequences


def test_process_consequences_with_none_values():
    # Test with None values to ensure graceful handling
    state = StoryState(
        current_node="start",
        depth=1,
        history=[],
        correct_answers=0,
        total_questions=0,
        previous_content=None,
        question_history=[],
    )

    consequences = process_consequences(state, None, None, None)
    assert consequences == ""
