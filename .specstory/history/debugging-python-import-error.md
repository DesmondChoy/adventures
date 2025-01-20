## SpecStory

## Debugging Python Import Error (1/20/2025, 9:59:39 PM)

_**User**_

Help me debug this?

---

_**Assistant**_

The error occurs because Python can't find the `database` module. This is likely because the import path isn't correct. Since your code is in the `app` directory, you need to modify the import statement to use the correct package path.

Here's the fix:

```python:app/init_data.py
# ... existing code ...
from app.database import SessionLocal, init_db
from app.database import StoryCategory, LessonTopic
# ... existing code ...
```

The change is simple - we just need to add `app.` before the database imports to tell Python to look for the database module within the app package.

To make this work, you'll also need to ensure:
1. There's an `__init__.py` file in your `app` directory (can be empty) to make it a proper Python package
2. You're running the script from the project root directory (where you currently are)

The error should be resolved after making this change. Let me know if you need any further assistance!

---

_**User**_

Help me debug this error

---

_**Assistant**_

I can help you debug this SyntaxError. The error occurs in `main.py` where there's a conflict between using `return` in an async generator function. The issue is in the second implementation of `generate_story_segment` function that uses `yield`.

Here's the problematic section:

```155:202:app/main.py
async def generate_story_segment(
    story_category: str, lesson_topic: str, state: StoryState
) -> StoryNode:
    """Generate the next story segment based on the current state."""
    # Load story configuration
    story_data = load_story_data()
    story_config = story_data["story_categories"][story_category]

    # Load lesson data if we're at the question depth
    question = None
    if state.depth == 1:  # Next node will be depth 2
        lesson_data = load_lesson_data()
        relevant_lessons = lesson_data[lesson_data["topic"] == lesson_topic]
        question = relevant_lessons.iloc[state.total_questions].to_dict()

    # Generate story content using LLM
    story_stream = await llm_service.generate_story_segment(
        story_config, state, question
    )

    # Process the streaming response
    story_content = ""
    story_choices = []

    # Accumulate the story content from the stream
    async for chunk in story_stream:
        if chunk.choices[0].delta.content:
            story_content += chunk.choices[0].delta.content
            # Send each chunk to the websocket
            yield chunk.choices[0].delta.content

    # Extract choices from the generated content
    # This is a simplified version - you might want to add more robust choice extraction
    if question:
        story_choices = [
            StoryChoice(text=question["correct_answer"], next_node="correct"),
            StoryChoice(text=question["wrong_answer1"], next_node="wrong1"),
            StoryChoice(text=question["wrong_answer2"], next_node="wrong2"),
        ]
    else:
        # For non-question nodes, look for choices in the generated content
        # This is where you'd implement choice extraction logic
        story_choices = [
            StoryChoice(text=f"Choice {i + 1}", next_node=f"node_{state.depth}_{i}")
            for i in range(2)
        ]
    return StoryNode(content=story_content, choices=story_choices)
```


The error occurs because this function both yields content (making it an async generator) and tries to return a value at the end, which is not allowed in Python. You can't both yield values and return a value in the same generator function.

Here's the fix:

```python
async def generate_story_segment(
    story_category: str, 
    lesson_topic: str, 
    state: StoryState
) -> StoryNode:
    """Generate the next story segment based on the current state."""
    # Load story configuration
    story_data = load_story_data()
    story_config = story_data["story_categories"][story_category]

    # Load lesson data if we're at the question depth
    question = None
    if state.depth == 1:  # Next node will be depth 2
        lesson_data = load_lesson_data()
        relevant_lessons = lesson_data[lesson_data["topic"] == lesson_topic]
        question = relevant_lessons.iloc[state.total_questions].to_dict()

    # Generate story content using LLM
    story_stream = await llm_service.generate_story_segment(
        story_config, state, question
    )

    # Process the streaming response
    story_content = ""
    story_choices = []

    # Accumulate the story content from the stream
    async for chunk in story_stream:
        if chunk.choices[0].delta.content:
            story_content += chunk.choices[0].delta.content

    # Extract choices based on whether this is a question node or not
    if question:
        story_choices = [
            StoryChoice(text=question["correct_answer"], next_node="correct"),
            StoryChoice(text=question["wrong_answer1"], next_node="wrong1"),
            StoryChoice(text=question["wrong_answer2"], next_node="wrong2"),
        ]
    else:
        story_choices = [
            StoryChoice(text=f"Choice {i + 1}", next_node=f"node_{state.depth}_{i}")
            for i in range(2)
        ]

    return StoryNode(content=story_content, choices=story_choices)
```app/main.py

The key changes are:
1. Removed the `yield` statement that was sending chunks to the websocket
2. Instead, we accumulate the content in the `story_content` variable
3. Return the complete `StoryNode` at the end

The streaming functionality should be handled at the websocket level instead. You'll need to modify the websocket handler to stream the content. Here's how you can modify the websocket handler:

```python
@app.websocket("/ws/story/{story_category}/{lesson_topic}")
async def story_websocket(websocket: WebSocket, story_category: str, lesson_topic: str):
    await websocket.accept()
    
    state = StoryState(
        current_node="start", depth=0, history=[], correct_answers=0, total_questions=0
    )

    try:
        while True:
            data = await websocket.receive_json()
            choice = data.get("choice")

            if choice is None:
                continue

            state.history.append(choice)
            state.depth += 1

            # Generate the complete story node
            story_node = await generate_story_segment(
                story_category, lesson_topic, state
            )

            # Stream the content word by word
            for word in story_node.content.split():
                await websocket.send_text(word + " ")
                await asyncio.sleep(0.1)

            # Send choices as a separate message
            await websocket.send_json({
                "type": "choices",
                "choices": [
                    {"text": choice.text, "id": choice.next_node}
                    for choice in story_node.choices
                ]
            })

    except WebSocketDisconnect:
        print(f"Client disconnected")
```

This should resolve the SyntaxError while maintaining the streaming functionality of your story generator.

---

_**User**_

Help me debug.

---

_**Assistant**_

I see the error - it's trying to import `StoryState` from `app.models.story` but that module doesn't exist. The `StoryState` class is actually defined in `main.py`. We need to reorganize the code structure to avoid circular imports.

Let's create a new models directory and move the Pydantic models there:

1. First, create this directory structure:
```app/main.py
app/
  models/
    __init__.py
    story.py
```

2. Create the story models file:

```python:app/models/story.py
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
```

3. Then modify main.py to import from the models module. In main.py, replace these lines:

```32:49:app/main.py
# Pydantic models for validation
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

```


with:

```python
from app.models.story import StoryChoice, StoryNode, StoryState
```

This reorganization will:
1. Prevent circular imports
2. Follow better code organization practices by separating models into their own module
3. Make the code more maintainable

The error should be resolved after making these changes. Let me know if you need any clarification or run into other issues!

---

_**User**_

I'm getting another error: 

---

_**Assistant**_



Ah, I see the issue. In `app/models/story.py`, you're trying to import from itself which creates a circular import. The line:

```python:app/models/story.py
from app.models.story import StoryChoice, StoryNode, StoryState
```

should be removed since these classes are being defined in this same file. Here's the correct version:

```python:app/models/story.py
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
```

The error occurred because the file was trying to import from itself while it was still being initialized. By removing that self-import, the circular dependency is resolved. Let me know if you need any clarification!

---



---

