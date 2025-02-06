from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Any, Optional


class StoryChoice(BaseModel):
    text: str
    next_node: str


class ChoiceHistory(BaseModel):
    node_id: str
    display_text: str


class StoryNode(BaseModel):
    content: str
    choices: List[StoryChoice]

    @field_validator("choices", mode="after")
    @classmethod
    def validate_choices(cls, v, values):
        if not v:
            raise ValueError("Must have at least one choice")
        # Story progression should have exactly 3 choices
        # Educational questions can have variable number of choices based on the database
        if len(v) < 3 and all(
            not c.next_node.startswith(("correct", "wrong")) for c in v
        ):
            raise ValueError("Story progression must have exactly 3 choices")
        return v


class QuestionHistory(BaseModel):
    question: Dict[str, Any]
    chosen_answer: str
    was_correct: bool


class StoryState(BaseModel):
    current_node: str
    chapter: int
    history: List[ChoiceHistory]
    correct_answers: int
    total_questions: int
    previous_content: Optional[str] = None
    question_history: List[QuestionHistory] = []  # Track all Q&A history
    story_length: int = Field(
        default=3, ge=3, le=7
    )  # Default to 3, must be between 3 and 7
