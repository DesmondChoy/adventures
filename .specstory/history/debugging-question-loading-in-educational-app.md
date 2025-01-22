## SpecStory

## Debugging Question Loading in Educational App (1/22/2025, 9:38:10 PM)

_**User**_

The functionality of this app is so at depth=1, the LLM tells a story and weaves in questions from load_lesson_data(). However, right now the questions at the end of depth=1 are self-generated. How can I fix it?

---

_**Assistant**_

Okay, I can help you investigate why the questions at depth=1 are not being pulled from `lessons.csv`.

Based on the code you've provided, the `generate_story_segment` function in `app/main.py` is responsible for loading lesson data and incorporating questions. Let's add some logging to this function to see if the questions are being loaded correctly.

Please modify the `generate_story_segment` function in `app/main.py` to include the following print statement after loading the question data:


```187:193:app/main.py
    # Load lesson data if we're at the question depth
    question = None
    if state.depth == 1:  # Next node will be depth 2
        lesson_data = load_lesson_data()
        relevant_lessons = lesson_data[lesson_data["topic"] == lesson_topic]
        question = relevant_lessons.iloc[state.total_questions].to_dict()

```

```python
    # Load lesson data if we're at the question depth
    question = None
    if state.depth == 1:  # Next node will be depth 2
        lesson_data = load_lesson_data()
        relevant_lessons = lesson_data[lesson_data["topic"] == lesson_topic]
        question = relevant_lessons.iloc[state.total_questions].to_dict()
        print(f"\nDEBUG: Loaded question at depth=1: {question}") # ADDED DEBUG LOG
```

After adding this line, run your application and start a story, selecting a lesson topic. Proceed through the story to depth=1. Then, check your console output for the "DEBUG: Loaded question at depth=1:" message.

This will help us determine if the questions are being loaded from `lessons.csv` as expected. Please share the console output after running the story with this debug log.

---

_**User**_

This is the debug log. It starts from depth=0 when telling the story (shouldn't it be depth=1?) and doesn't present choices from load_lesson_data()

---

_**Assistant**_

The debug log you provided is helpful, but it doesn't show the output from the debug print statement we added in `app/main.py`.  It's crucial to see if the question loading is happening at all.

Could you please provide the *complete* console output after running the application and going through depth=0 and reaching depth=1?  Make sure to include everything printed in the console, especially look for the line that starts with:

```
DEBUG: Loaded question at depth=1:
```

This line should appear in your console output if the code in `app/main.py` is executing correctly and attempting to load a question at depth=1.

Regarding your question about the depth:

*   **Depth 0:**  Should be the story introduction, as you correctly pointed out.
*   **Depth 1:** Should be when the educational question is presented, based on your app's intended functionality.
*   **Depth 2 and 3:**  Likely story continuation and conclusion, potentially with consequences based on the answer to the question at depth 1.

The debug log you provided shows "Depth: 0 of 3" and then "Depth: 2 of 3", which suggests that depth=1 might be skipped or not behaving as expected.

Once you provide the complete console output including the "DEBUG: Loaded question..." line (or the absence of it), we can better understand if the questions are being loaded and why they might not be appearing in your story.

---

_**User**_

I did a ctrl-f for "Loaded question at depth=1:" and it doesn't show up

---

_**Assistant**_

Okay, the fact that "Loaded question at depth=1:" doesn't appear in your logs strongly suggests that the code block responsible for loading questions at depth=1 is not being executed.

Let's re-examine the `generate_story_segment` function in `app/main.py` to make sure the debug print is correctly placed within the `if state.depth == 1:` condition.

```python:app/main.py
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
        print(f"\nDEBUG: Loaded question at depth=1: {question}") # DEBUG LOG - ENSURE THIS IS INSIDE THE IF BLOCK

    # Generate story content using LLM
    story_stream = await llm_service.generate_story_segment(
        story_config, state, question
    )

    # Process the streaming response
    story_content = ""
    story_choices = []
    # ... rest of the function ...
```

**Please double-check:**

1.  **Is the `print(f"\nDEBUG: Loaded question at depth=1: {question}")` line definitely indented and inside the `if state.depth == 1:` block?**  Incorrect indentation would cause it to execute at a different time or not at all when `state.depth == 1`.
2.  **Is there any chance you are running an older version of the code where you hadn't added this debug print yet?**  Sometimes we can accidentally run an outdated version of the application.

If you confirm that the debug print is correctly placed and you are running the latest code, then the issue is likely that `state.depth` is not equal to `1` when you expect it to be.

To investigate this, we need to trace back how `state.depth` is being set and updated. Could you please provide the code where `generate_story_segment` is called and how the `StoryState` object is created and updated as the user progresses through the story?  Specifically, look for where `state.depth` is initialized and incremented. This might be in your frontend JavaScript code (handling page navigation) or in the backend Python code that manages the story flow.

---



---

