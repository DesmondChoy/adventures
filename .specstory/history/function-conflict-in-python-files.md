## SpecStory

## Function Conflict in Python Files (1/22/2025, 9:36:01 PM)

_**User**_

I see main.py has a defintion for generate_story_segment(), and so does llm.py. Will that cause any conflicts?

---

_**Assistant**_

Let me check both files to understand how these functions are defined and their relationship.

---

_**Assistant**_



---

_**Assistant**_



---

_**Assistant**_



No, there won't be any conflicts. Here's why:

1. In `main.py`, `generate_story_segment()` is a high-level function that orchestrates the story generation process. It:
   - Takes story category, lesson topic, and state as parameters
   - Loads story configuration and lesson data
   - Calls the LLM service's `generate_story_segment()`
   - Processes the response to create a `StoryNode` with content and choices

2. In `llm.py`, `generate_story_segment()` is a method of the `LLMService` class that specifically handles the LLM interaction. It:
   - Takes story config, state, and question as parameters
   - Builds prompts for the LLM
   - Makes the actual API call to OpenAI
   - Returns the streaming response

The two functions work together - the one in `main.py` calls the one in `llm.py` through the `llm_service` instance. You can see this in `main.py` line 183:

```python
story_stream = await llm_service.generate_story_segment(
    story_config, state, question
)
```

This is a common pattern where you have a high-level orchestration function calling a more specialized service method. They have different responsibilities and work in harmony.

---

_**User**_

But they should be named differently to avoid confusion?

---

_**Assistant**_

Yes, you make a good point. Having two functions with the same name, even in different modules, can be confusing for developers reading and maintaining the code. Let me rename the function in `main.py` to better reflect its orchestration role.

---

_**Assistant**_

```
// ... existing code ...
async def generate_story_node(
    story_category: str, lesson_topic: str, state: StoryState
) -> StoryNode:
    """Generate the next story segment based on the current state."""
// ... existing code ...
                # Generate the complete story node
                story_node = await generate_story_node(
                    story_category, lesson_topic, state
                )
// ... existing code ...
```

---

_**Assistant**_



I've renamed the function in `main.py` from `generate_story_segment` to `generate_story_node`. This new name better reflects what the function actually does - it generates a complete `StoryNode` object that contains both the story content and the available choices.

Now the distinction between the two functions is clearer:
- `LLMService.generate_story_segment()` - handles the raw story generation via the LLM
- `generate_story_node()` - orchestrates the full node creation process, including choices and question integration

This makes the code more self-documenting and easier to understand.

---

_**User**_

The functionality of this app is so at depth=1, the LLM tells a story and weaves in questions from load_lesson_data(). However, right now the questions at the end of depth=1 are self-generated. How can I fix it?

---

_**Assistant**_

Ah, I see the issue. Looking at the code, even though we're loading the question at depth=1, we're not properly integrating it into the story choices. The LLM is generating its own story with choices, but we need to ensure the choices from the loaded question are used.

Let me modify the code to fix this:

---

_**Assistant**_

```
async def generate_story_node(
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

    try:
        async for chunk in story_stream:
            if chunk.choices[0].delta.content:
                story_content += chunk.choices[0].delta.content
    except Exception as e:
        print(f"Error during story generation: {e}")
        story_content = "I apologize, but I encountered an error generating the story. Please try again."

    # Set up choices based on story depth
    if state.depth == 1:
        if not question:
            raise ValueError("Question not found for depth 1")
        # Ensure the question is appended to the story content
        story_content += f"\n\n{question['question']}"
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
```

---

_**Assistant**_



I've made several important changes to fix the issue:

1. Removed the debug print statement since it's no longer needed
2. Made the choice selection more explicit based on `state.depth`
3. Added a validation check to ensure we have a question at depth 1
4. Most importantly, I'm now explicitly appending the question to the story content with `story_content += f"\n\n{question['question']}"` 

The key changes ensure that:
1. At depth 1, we always use the question from `lessons.csv` 
2. The question is explicitly added to the story content
3. The choices are always the actual answers from the lesson data, not LLM-generated ones

The LLM will still generate the story content leading up to the question, but now the question and its choices will come directly from your lesson data. This ensures consistency with your educational content while maintaining the engaging storytelling aspect.

---

_**User**_

Is depth=0 the first page of the story (after "Start Adventure" has been clicked"), or is it depth=1?

---

_**Assistant**_

Looking at the code, depth=0 is the first page of the story after "Start Adventure" is clicked. Here's how we can tell:

1. In the WebSocket handler, the state is initialized with depth=0:
```python
state = StoryState(
    current_node="start", depth=0, history=[], correct_answers=0, total_questions=0
)
```

2. The depth only increments when a choice is made:
```python
if choice != "start":  # Don't append "start" to history
    state.history.append(choice)
    state.depth += 1
```

3. In `generate_story_node`, we can see that depth=1 is specifically treated as the question depth:
```python
if state.depth == 1:  # Next node will be depth 2
    lesson_data = load_lesson_data()
    relevant_lessons = lesson_data[lesson_data["topic"] == lesson_topic]
    question = relevant_lessons.iloc[state.total_questions].to_dict()
```

So the progression is:
- depth=0: Initial story page (after clicking "Start Adventure")
- depth=1: First choice leads here, where a question is integrated
- depth=2 and depth=3: Further story progression after answering the question

---

_**User**_

Make it so that depth=1 is the first page of the story after "Start Adventure" is clicked. It's more intuitive.

---

_**Assistant**_

I'll modify the code to make depth=1 the starting depth. This will require changes to the initial state and the depth increment logic.

---

_**Assistant**_

```
    # Initialize with default state
    state = StoryState(
        current_node="start", depth=1, history=[], correct_answers=0, total_questions=0
    )

    try:
        while True:
            data = await websocket.receive_json()
            choice = data.get("choice")

            # If we receive a state update, use it to initialize our state
            if "state" in data:
                state = StoryState(
                    current_node=data["state"].get("current_node", "start"),
                    depth=data["state"].get("depth", 1),  # Default to 1 instead of 0
                    history=data["state"].get("history", []),
                    correct_answers=data["state"].get("correct_answers", 0),
                    total_questions=data["state"].get("total_questions", 0),
                )
                continue  # Skip to next iteration to wait for choice

            if choice is None:
                continue

            # Only append choice and increment depth for non-state messages
            if choice != "start":  # Don't append "start" to history
                state.history.append(choice)
                state.depth += 1

// ... existing code ...

    # Set up choices based on story depth
    if state.depth == 2:  # Changed from 1 to 2 since we start at depth 1
        if not question:
            raise ValueError("Question not found for depth 2")
        # Ensure the question is appended to the story content
        story_content += f"\n\n{question['question']}"
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
```

---

_**Assistant**_



I've made the following changes:
1. Changed the initial state depth from 0 to 1
2. Updated the default depth in the state update logic from 0 to 1
3. Changed the question depth check from 1 to 2 (since we now start at 1)
4. Updated the error message to reflect the new depth

Now the story progression will be:
- depth=1: Initial story page (after clicking "Start Adventure")
- depth=2: First choice leads here, where a question is integrated
- depth=3 and depth=4: Further story progression after answering the question

This should feel more intuitive since we start counting from 1 rather than 0.

---

_**User**_

No the question depth check should still be at depth=1.

---

_**Assistant**_



Ah, I apologize for the confusion. You're right - we want the question to appear on the first page (depth=1) after clicking "Start Adventure". Let me fix that.

---

_**Assistant**_

```
    # Load lesson data if we're at the question depth
    question = None
    if state.depth == 1:  # Question appears on first page
        lesson_data = load_lesson_data()
        relevant_lessons = lesson_data[lesson_data["topic"] == lesson_topic]
        question = relevant_lessons.iloc[state.total_questions].to_dict()

    # Generate story content using LLM
    story_stream = await llm_service.generate_story_segment(
        story_config, state, question
    )

    # Process the streaming response
    story_content = ""

    try:
        async for chunk in story_stream:
            if chunk.choices[0].delta.content:
                story_content += chunk.choices[0].delta.content
    except Exception as e:
        print(f"Error during story generation: {e}")
        story_content = "I apologize, but I encountered an error generating the story. Please try again."

    # Set up choices based on story depth
    if state.depth == 1:
        if not question:
            raise ValueError("Question not found for depth 1")
        # Ensure the question is appended to the story content
        story_content += f"\n\n{question['question']}"
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
```

---

_**Assistant**_



Now the flow will be:
1. User clicks "Start Adventure"
2. First page (depth=1) shows the story with an integrated question and answer choices
3. After answering, depth increments to 2 for the next part of the story

This makes more sense - the user immediately gets into the interactive educational content starting with depth=1.

---

_**User**_

In the debug log, it's still indicated that it's starting at depth=0: 



---

_**Assistant**_

Ah yes, we need to update the prompt being sent to the LLM service as well. Let me check the LLM service code.

---

_**Assistant**_



---

_**Assistant**_



I see the issue. In `llm.py`, the `_build_user_prompt` method is still checking for `state.depth == 0` to generate the opening scene. Let me update that:

---

_**Assistant**_

```
    def _build_user_prompt(
        self,
        story_config: Dict[str, Any],
        state: StoryState,
        question: Optional[Dict[str, Any]],
    ) -> str:
        """Create a user prompt that includes story state and current requirements."""
        prompt = f"""Current story state:
- Depth: {state.depth} of 3
- Previous choices: {", ".join(state.history) if state.history else "Story beginning"}

"""

        if state.depth == 1 and not state.history:  # Opening scene at depth 1
            prompt += "Generate the opening scene of the story, introducing the setting and main character."
        elif question:
            # Integrate educational question naturally into the story
            prompt += f"""Continue the story, naturally leading to a situation where the following question 
            can be asked: {question["question"]}

The choices should be:
1. {question["correct_answer"]}
2. {question["wrong_answer1"]}
3. {question["wrong_answer2"]}

The question should feel like a natural part of the story's progression."""
        else:
            # Regular story continuation
            prompt += """Continue the story based on the previous choices, 
            creating meaningful consequences for the character's decisions.
            
End this segment with two clear choices that would lead the story in different directions."""

        return prompt
```

---

_**Assistant**_



I've made two important changes to the `_build_user_prompt` method:
1. Changed the depth check from `state.depth == 0` to `state.depth == 1`
2. Added `and not state.history` to ensure we only generate the opening scene when it's the very first page (depth=1 with no previous choices)

Now the debug log should show depth=1 when starting the story, and the opening scene will be generated at depth=1 instead of depth=0.

---

_**User**_

It's still showing Depth: 0 of 3

---

_**Assistant**_



Looking at the debug log, I see the issue. Even though we changed the initial state to depth=1 in both files, the debug output still shows depth=0. Let me check the state being passed to the LLM service.

---

_**Assistant**_



---

_**Assistant**_



Ah, I see the problem. Even though we updated the state initialization in one place, there's another initialization in the websocket handler that's still using depth=0. Let me fix that:

---

_**Assistant**_

```
    # Initialize with default state
    state = StoryState(
        current_node="start", depth=1, history=[], correct_answers=0, total_questions=0
    )

    try:
        while True:
            data = await websocket.receive_json()
            choice = data.get("choice")

            # If we receive a state update, use it to initialize our state
            if "state" in data:
                state = StoryState(
                    current_node=data["state"].get("current_node", "start"),
                    depth=data["state"].get("depth", 1),  # Default to 1 instead of 0
                    history=data["state"].get("history", []),
                    correct_answers=data["state"].get("correct_answers", 0),
                    total_questions=data["state"].get("total_questions", 0),
                )
```

---

_**Assistant**_







I've updated both places where the state is initialized in the websocket handler:
1. The initial state creation now starts with `depth=1`
2. The state update from client data now defaults to `depth=1` instead of `depth=0`

Now when you start the story, the debug log should show "Depth: 1 of 3" instead of "Depth: 0 of 3", and the story will properly begin at depth=1.

---

_**Assistant**_



---



---

