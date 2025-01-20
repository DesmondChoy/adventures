from pydantic import BaseModel
from typing import List


class StoryChoice(BaseModel):
    text: str
    next_node: str


class StoryNode(BaseModel):
    content: str
    choices: List[StoryChoice]


class StoryState(BaseModel):
    current_node: str
    depth: int
    history: List[str]
    correct_answers: int
    total_questions: int
