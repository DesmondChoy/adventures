from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


class StoryChoice(BaseModel):
    text: str
    next_node: str


class ChoiceHistory(BaseModel):
    node_id: str
    display_text: str


class StoryChoices(BaseModel):
    """Structured format for story choices."""

    choices: List[str] = Field(
        min_length=2, max_length=2, description="List of exactly two narrative choices"
    )


class StoryNode(BaseModel):
    content: str
    choices: List[StoryChoice]


class QuestionHistory(BaseModel):
    question: Dict[str, Any]
    chosen_answer: str
    was_correct: bool


class StoryState(BaseModel):
    current_node: str
    depth: int
    history: List[ChoiceHistory]
    correct_answers: int
    total_questions: int
    previous_content: Optional[str] = None
    question_history: List[QuestionHistory] = []  # Track all Q&A history
