from pydantic import BaseModel
from typing import List, Dict, Any, Optional


class StoryChoice(BaseModel):
    text: str
    next_node: str


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
    history: List[str]
    correct_answers: int
    total_questions: int
    previous_content: Optional[str] = None
    question_history: List[QuestionHistory] = []  # Track all Q&A history
