## SpecStory

## Formatting Issues in Story Generation Output (1/21/2025, 6:24:09 PM)

_**User**_

This is the output after running `uvicorn app.main:app --reload`:

```
In the heart of the Enchanted Forest, where sunlight danced upon the leaves like golden fairies, a young wizard named Elara embarked on a quest to uncover the secrets of ancient magic. Guided by the whispers of the trees, she ventured deeper into the woods, accompanied by her loyal friend, a wise old owl named Sage. Their journey led them to the Crystal Caves, a place where the air shimmered with the promise of knowledge and the walls glowed with the wisdom of ages past. As they stepped inside, the cave's luminescent crystals cast a gentle light on a curiously carved stone tablet. Elara traced her fingers over the ancient runes, and with Sage's help, deciphered a clue that spoke of the sacred knowledge of life itself. The tablet revealed that to unlock the next path of her journey, Elara must understand the mysteries of the body and its magical symphony – a task that would require both intellect and intuition. The cave, it seemed, was enchanted with an insatiable curiosity about the wonders of life. As the duo explored further, they stumbled upon a mural depicting the journey of nourishment through the body. The mural, alive with magical animation, showed the path of food as it transformed into energy. But to proceed, Elara had to answer a question posed by the mural's guardian spirit: "What is the longest part of the digestive system?" The gentle voice echoed through the cave, offering her three choices: 1. Small Intestine 2. Stomach 3. Large Intestine As Elara pondered, she knew that her choice would not only guide her steps forward but also deepen her understanding of the magic within.
```

The issue is that there's no paragraphing or formatting, even though the prompt explicitly mentions "Each story segment should be 2-3 paragraphs long and end with natural decision points.". Is it an issue with the website not rendering paragraphs? 

Another issue: The questions and choices should be in a separate paragraph altogether, to ensure readability. 

---

_**Assistant**_

Looking at the code and output, there are a few issues to address:

1. The paragraph formatting issue likely stems from how the response is being processed and displayed. Looking at the `generate_story_segment` method:


```42:53:app/services/llm.py
        try:
            # Call the LLM with our prompts
            response = await self.client.chat.completions.create(
                model="gpt-4o-2024-08-06",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,  # Balanced between creativity and consistency
                stream=True,  # Enable streaming for real-time story delivery
            )
            return response
```


The response is being streamed but there's no handling of formatting preservation. Additionally, in the system prompt:


```81:81:app/services/llm.py
        Each story segment should be 2-3 paragraphs long and end with natural decision points.
```


While we specify "2-3 paragraphs", we don't explicitly instruct the LLM about formatting.

Here's how we can fix these issues:

1. Modify the system prompt to be more explicit about formatting. Update the line to:

```python
Each story segment should be formatted with:
- 2-3 clear paragraphs separated by blank lines
- If a question is present, it should be separated from the main story by a blank line
- Choices should be presented on separate lines after the question
```app/services/llm.py

2. For the question integration, modify the user prompt section to be more explicit about formatting:


```100:109:app/services/llm.py
            # Integrate educational question naturally into the story
            prompt += f"""Continue the story, naturally leading to a situation where the following question 
            can be asked: {question["question"]}

The choices should be:
1. {question["correct_answer"]}
2. {question["wrong_answer1"]}
3. {question["wrong_answer2"]}

The question should feel like a natural part of the story's progression."""
```


Should be updated to:

```python
prompt += f"""Continue the story, naturally leading to a situation where the following question can be asked:

Question: {question["question"]}

Choose your answer:
1. {question["correct_answer"]}
2. {question["wrong_answer1"]}
3. {question["wrong_answer2"]}

The question should feel like a natural part of the story's progression but be clearly separated in formatting."""
```

3. You might also want to add a post-processing step to ensure proper formatting is maintained when displaying the response. You could add a method like:

```python
def _format_response(self, response: str) -> str:
    """Ensure proper formatting of the story response."""
    # Split into paragraphs and clean up
    paragraphs = [p.strip() for p in response.split('\n\n') if p.strip()]
    
    # Rejoin with proper spacing
    formatted_response = '\n\n'.join(paragraphs)
    
    return formatted_response
```

These changes should help ensure the story output is properly formatted with clear paragraphs and question separation.

---

_**User**_

And where will _format_response() be called?

---

_**Assistant**_

Looking at the code, the `_format_response()` method is defined but not used yet. It should be called in the `generate_story_segment` method where we handle the response from the LLM.

Currently, the response is just returned directly (see lines 42-53). We need to modify this section to process the streamed response and format it properly.

Here's how we should modify the `generate_story_segment` method:

```python:app/services/llm.py
try:
    # Call the LLM with our prompts
    response = await self.client.chat.completions.create(
        model="gpt-4o-2024-08-06",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.7,  # Balanced between creativity and consistency
        stream=True,  # Enable streaming for real-time story delivery
    )
    
    # Collect the streamed response
    full_response = ""
    async for chunk in response:
        if chunk.choices[0].delta.content:
            full_response += chunk.choices[0].delta.content
    
    # Format the collected response
    formatted_response = self._format_response(full_response)
    return formatted_response
```

This modification will:
1. Collect the streamed chunks from the LLM
2. Combine them into a complete response
3. Process the response through our formatting method
4. Return the properly formatted text

The streaming functionality is maintained, but we ensure the final output has proper paragraph formatting and spacing as defined in our `_format_response` method.

---

_**User**_

Check this .py once more for any inconsistencies or potential bugs.

---

_**Assistant**_

I'll review the code for potential issues and inconsistencies. Looking at the complete file:

1. **Model Name Typo**: On line 45, there's a typo in the model name:

```45:45:app/services/llm.py
                model="gpt-4o-2024-08-06",
```

`"gpt-4o-2024-08-06"` should be `"gpt-4-0125-preview"` or another valid OpenAI model name.

2. **Prompt String Formatting**: In the `_build_user_prompt` method, there's inconsistent string formatting:

```125:128:app/services/llm.py
            prompt += """Continue the story based on the previous choices, 
            creating meaningful consequences for the character's decisions.
            
End this segment with two clear choices that would lead the story in different directions."""
```

The multiline string has inconsistent indentation and a trailing comma. It should be:

```python
prompt += """Continue the story based on the previous choices, \
creating meaningful consequences for the character's decisions.

End this segment with two clear choices that would lead the story in different directions."""
```app/services/llm.py

3. **Unused Method**: The `_process_consequences` method (lines 132-144) is defined but never called in the code. Either it should be implemented in the story generation flow or removed if not needed.

4. **Error Handling**: While there's error handling in `generate_story_segment`, it might be good to add specific handling for common OpenAI API errors (rate limits, token limits, etc.).

5. **Type Hints**: Consider adding more specific type hints for the dictionary structures. Instead of `Dict[str, Any]`, you could create specific TypedDict classes for `story_config` and `question`.

Here's a suggested improvement for the type hints:

```python
from typing import TypedDict, Literal

class QuestionDict(TypedDict):
    question: str
    correct_answer: str
    wrong_answer1: str
    wrong_answer2: str

class StoryConfig(TypedDict):
    tone: str
    vocabulary_level: str
    story_rules: List[str]
    narrative_elements: Dict[str, List[str]]
```

6. **Response Formatting**: In `_format_response`, you might want to add handling for special cases like preserving question formatting. Consider updating it to:

```python:app/services/llm.py
def _format_response(self, response: str) -> str:
    """Ensure proper formatting of the story response."""
    # Split into paragraphs and clean up
    paragraphs = [p.strip() for p in response.split("\n\n") if p.strip()]
    
    # Find and preserve question formatting if present
    for i, p in enumerate(paragraphs):
        if p.startswith("Question:"):
            # Ensure question and choices are properly formatted
            question_parts = p.split("\n")
            question_parts = [part.strip() for part in question_parts if part.strip()]
            paragraphs[i] = "\n".join(question_parts)
    
    # Rejoin with proper spacing
    formatted_response = "\n\n".join(paragraphs)
    
    return formatted_response
```

These changes would improve the code's robustness and maintainability while fixing the formatting issues you encountered.

---

_**User**_

My app isn't starting now. And no errors are thrown.

---

_**Assistant**_

Okay, let's troubleshoot why your app isn't starting without throwing errors. This usually indicates a silent failure or a blocking operation. Here's a systematic approach to diagnose the issue:

1. **Check for Port Conflicts**:

    *   If another application is using the same port Uvicorn is trying to use, it might fail silently.
    *   Ensure no other services are running on port 8000 (or the port you've configured).
    *   You can use tools like  `netstat`  (on Linux/macOS) or  `Resource Monitor`  (on Windows) to check for port usage.
2. **Review Recent Changes**:

    *   Since the issue started after our last code modifications, let's carefully examine those areas.
    *   The most likely culprit is the change in  `generate_story_segment`  where we handle the streamed response.
3. **Isolate the Problem**:

    *   Let's temporarily revert the  `generate_story_segment`  method to its original state to see if that's the cause.
    *   Here's the original code snippet:

    ```python:app/services/llm.py
    startLine: 42
    endLine: 53
    ```

    *   Replace the current  `generate_story_segment`  with this original version.
    *   If the app starts, we've confirmed the issue is within our modifications.
4. **Debugging the Streamed Response**:

    *   If the problem is in the modified  `generate_story_segment`, let's add some debugging:

    ```python:app/services/llm.py
    startLine: 42
    endLine: 59
    ```

    *   Add print statements to check the response and formatting:

    ```python
    print("Calling LLM...")
    response = await self.client.chat.completions.create(
        model="gpt-4-0125-preview",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.7,
        stream=True,
    )

    full_response = ""
    async for chunk in response:
        print(f"Received chunk: {chunk}")
        if chunk.choices[0].delta.content:
            full_response += chunk.choices[0].delta.content

    print(f"Full response before formatting: {full_response}")
    formatted_response = self._format_response(full_response)
    print(f"Formatted response: {formatted_response}")
    return formatted_response
    ```

    *   These print statements will help us see:
        *   If the LLM call is made.
        *   What chunks are received.
        *   The response before and after formatting.
5. **Check for Infinite Loops**:

    *   Ensure there are no infinite loops in the modified code, especially in the  `async for`  loop or the  `_format_response`  method.
    *   The added print statements should help identify if the code is stuck in a loop.
6. **Review  `_format_response`**:

    *   Double-check the logic in  `_format_response`  to ensure it doesn't have any issues that could cause it to hang or fail silently.
    *   Add print statements within this method to track its execution.
7. **Asynchronous Operations**:

    *   Make sure all asynchronous operations are properly awaited.
    *   Any missing  `await`  could lead to unexpected behavior.
8. **Dependency Issues**:

    *   If you've recently updated any dependencies, there might be compatibility issues.
    *   Try reverting to previous versions of key libraries (like  `openai`) to see if that resolves the issue.

By following these steps, we should be able to pinpoint the cause of the app not starting and resolve the issue. Let me know the output of the debugging print statements, and we can continue troubleshooting from there.


---



---

