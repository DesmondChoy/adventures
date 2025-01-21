## SpecStory

## Improving Story Formatting and Readability (1/21/2025, 6:45:41 PM)

_**User**_

This is the app's output after running `uvicorn app.main:app --reload`:

```
In the heart of the Whispering Woods, where ancient trees mingled their boughs to form a natural cathedral, a young wizard named Elara embarked on her first solo quest. Her mentor, the venerable owl known as Professor Hootsworth, had tasked her with retrieving a rare herb known as the Moonleaf, said to bloom only under the light of the full moon. This herb was crucial for concocting a potion to aid the forest's ailing creatures, and Elara felt the weight of her responsibility. As Elara ventured deeper into the forest, the path led her to the entrance of the Crystal Caves, where the air was thick with enchantment. Inside, the caves glimmered with a kaleidoscope of colors, casting dancing shadows on the walls. Here, she encountered a peculiar creature—a wise, ageless tortoise named Tormund, whose shell shimmered with the colors of the rainbow. Tormund was known far and wide for his knowledge of the forest and its secrets. "Ah, young Elara," Tormund greeted in a voice like the rustle of leaves, "I see you seek the Moonleaf. But first, a test of wisdom. Tell me, what is the longest part of the digestive system? Each answer holds a different path, and only the correct one will lead you to the Moonleaf's hidden grove." Elara pondered the question, knowing that her answer would determine the path ahead. Should she choose the Small Intestine, the Stomach, or the Large Intestine?
```

The issue is that there's no paragraphing or formatting, even though the prompt explicitly mentions "Each story segment should be 2-3 paragraphs long and end with natural decision points.". Is it an issue with the website not rendering paragraphs? 

Another issue: The questions and choices should be in a separate paragraph altogether, to ensure readability.

---

_**Assistant**_

Below is a suggested update to your system prompt to remind the LLM to preserve paragraph boundaries and place the question and choices in a new paragraph. This should help ensure the story is consistently chunked into multiple paragraphs and that the choices appear separately:

Explain the edits to app/services/llm.py:
```python:app/services/llm.py
# ...
def _build_system_prompt(self, story_config: Dict[str, Any]) -> str:
    """Create a system prompt that establishes the storytelling framework."""
    return f"""
        You are a master storyteller crafting an interactive educational story.
        
        Writing Style:
        - Maintain a {story_config["tone"]} tone throughout the narrative
        - Use vocabulary appropriate for {story_config["vocabulary_level"]}
        - Follow these story rules: {", ".join(story_config["story_rules"])}

        Story Elements to Include:
        - Setting types: {", ".join(story_config["narrative_elements"]["setting_types"])}
        - Character archetypes: {", ".join(story_config["narrative_elements"]["character_archetypes"])}

        Your task is to generate engaging story segments that:
        1. Maintain narrative consistency with previous choices
        2. Create meaningful consequences for user decisions
        3. Seamlessly integrate educational elements when provided
        4. End each segment with clear choice points that advance the story
        5. Use multiple paragraphs separated by blank lines to ensure readability.
           The question and its choices, if any, should appear in a separate paragraph from the main narrative.
        """
# ...
```

Explanation:
• The new item (number 5) explicitly instructs the model to return text in multiple paragraphs (with blank lines in between) and to place educational questions and choices in a new paragraph. This helps ensure readability and clearer separation of story text from question prompts.  

Please note that if the rendering environment (e.g., your front-end or website) strips out or fails to interpret line breaks, you may also need to ensure that newlines in responses are preserved or displayed as HTML paragraphs.

---

_**User**_

The paragraphs and formatting still aren't being reflected.

---

_**Assistant**_

Let me check how the response is being handled. I'll search for relevant code that processes the LLM response.

---

_**Assistant**_



---

_**Assistant**_



Looking at the code, I can see that the issue is likely in how the response is being displayed in the frontend. The LLM response is being streamed word by word and appended to the HTML using:

```javascript
function appendStoryText(text) {
    const storyContent = document.getElementById('storyContent');
    storyContent.innerHTML += text;
    // Auto-scroll to keep up with the story
    storyContent.scrollTop = storyContent.scrollHeight;
}
```

The issue is that we're just concatenating the text without preserving newlines. Let's modify the frontend to properly handle newlines and formatting. I'll update the code:

---

_**Assistant**_

```
// ... existing code ...
        function appendStoryText(text) {
            const storyContent = document.getElementById('storyContent');
            // Replace newlines with <br> tags and preserve whitespace
            storyContent.style.whiteSpace = 'pre-wrap';
            storyContent.innerHTML += text;
            // Auto-scroll to keep up with the story
            storyContent.scrollTop = storyContent.scrollHeight;
        }
// ... existing code ...
```

---

_**Assistant**_



Now let's also modify the WebSocket handler to ensure we're sending complete paragraphs instead of individual words:

---

_**Assistant**_

```
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

            # Split into paragraphs and stream each paragraph
            paragraphs = story_node.content.split('\n\n')
            for paragraph in paragraphs:
                if paragraph.strip():  # Only send non-empty paragraphs
                    await websocket.send_text(paragraph.strip() + '\n\n')
                    await asyncio.sleep(0.5)  # Pause between paragraphs for dramatic effect
// ... existing code ...
```

---

_**Assistant**_



These changes should now:

1. Preserve whitespace and newlines in the frontend display using `white-space: pre-wrap`
2. Stream complete paragraphs instead of individual words
3. Add proper spacing between paragraphs with `\n\n`
4. Add a dramatic pause between paragraphs for better readability

Try running the application again and you should see properly formatted paragraphs with clear separation between story text and choices.

---

_**User**_

The paragraphs and formatting are showing up now. But the very first paragraph displayed has an issue:

```

                    
                In the heart of the Enchanted Forest, where the trees whispered ancient secrets and the air shimmered with unseen magic, young wizard Aeliana embarked on her first grand adventure. Her mentor, the wise and gentle Elderberry, had entrusted her with a crucial task: to deliver a message of great importance to the Crystal Caverns, where the Luminescent Council awaited.
```

Why is there so much white space?

---

_**Assistant**_

The issue is coming from how the HTML is structured and how we're appending text. Looking at the HTML, there's a div with class "prose" that's initially empty, and when we append text, we're preserving all whitespace including the initial empty space.

Let me fix this by modifying both the HTML structure and the append function:

---

_**Assistant**_

```
// ... existing code ...
            <div class="bg-white rounded-xl shadow-md p-6">
                <div id="storyContent" class="prose max-w-none mb-6 whitespace-pre-wrap"></div>
                <div id="choicesContainer" class="space-y-3">
                    <!-- Choices will be inserted here -->
                </div>
            </div>
// ... existing code ...
        function appendStoryText(text) {
            const storyContent = document.getElementById('storyContent');
            // Trim any leading/trailing whitespace from the text
            const trimmedText = text.trim();
            if (trimmedText) {
                storyContent.innerHTML += trimmedText;
                // Auto-scroll to keep up with the story
                storyContent.scrollTop = storyContent.scrollHeight;
            }
        }
// ... existing code ...
```

---

_**Assistant**_



The changes I made:
1. Removed the empty comment inside the story content div that was causing initial whitespace
2. Moved `whitespace-pre-wrap` to the class list instead of setting it via JavaScript
3. Added trimming of text before appending to remove any leading/trailing whitespace
4. Added a check to only append non-empty text

This should now display the story text without any extra whitespace at the beginning. The paragraphs will still be properly formatted with the whitespace between them preserved, but without the unnecessary leading space.

---

_**User**_

The whitespace is gone now, but so are the paragraphing and formatting.

---

_**Assistant**_

Ah, I see the issue. We need to preserve the newlines between paragraphs while trimming only the leading/trailing whitespace. Let's modify the code to handle this correctly:

---

_**Assistant**_

```
            # Generate the complete story node
            story_node = await generate_story_segment(
                story_category, lesson_topic, state
            )

            # Split into paragraphs and stream each paragraph
            paragraphs = [p.strip() for p in story_node.content.split('\n\n') if p.strip()]
            
            # Send the first paragraph without a leading newline
            if paragraphs:
                await websocket.send_text(paragraphs[0])
                await asyncio.sleep(0.5)
            
            # Send remaining paragraphs with consistent double newlines
            for paragraph in paragraphs[1:]:
                await websocket.send_text('\n\n' + paragraph)
                await asyncio.sleep(0.5)  # Pause between paragraphs for dramatic effect

            # Send choices as a separate message
// ... existing code ...
```

---

_**Assistant**_

```
        function appendStoryText(text) {
            const storyContent = document.getElementById('storyContent');
            // Append text while preserving newlines
            storyContent.innerHTML += text;
            // Auto-scroll to keep up with the story
            storyContent.scrollTop = storyContent.scrollHeight;
        }
// ... existing code ...
```

---

_**Assistant**_



The changes I made:

1. In `main.py`:
   - Clean up paragraphs by stripping whitespace from each one while preserving paragraph structure
   - Send the first paragraph without any leading newlines
   - Send subsequent paragraphs with consistent double newlines before them
   
2. In `index.html`:
   - Simplified the `appendStoryText` function to just append the text as-is
   - Rely on the server-side formatting to ensure proper paragraph spacing
   - Keep the `whitespace-pre-wrap` class to preserve the formatting

This should now:
1. Show no extra whitespace at the start of the story
2. Maintain proper paragraph spacing between paragraphs
3. Keep the text formatting consistent throughout the story

Try running the application again - you should see clean formatting with proper paragraph breaks.

---

_**User**_

The paragraphs and formatting are now showing up. However, it seems like the app is streaming each paragraph, instead of streaming each word. The whole paragraph shows up as a chunk together. I want each word to be streamed.

---

_**Assistant**_

Ah, I see. We need to modify the streaming to happen at the word level while still maintaining paragraph formatting. Let's update the WebSocket handler:

---

_**Assistant**_

```
            # Generate the complete story node
            story_node = await generate_story_segment(
                story_category, lesson_topic, state
            )

            # Split into paragraphs and stream each word while maintaining paragraph structure
            paragraphs = [p.strip() for p in story_node.content.split("\n\n") if p.strip()]
            
            # Process first paragraph
            if paragraphs:
                words = paragraphs[0].split()
                for word in words:
                    await websocket.send_text(word + " ")
                    await asyncio.sleep(0.05)  # Small delay between words
            
            # Process remaining paragraphs
            for paragraph in paragraphs[1:]:
                # Send paragraph break
                await websocket.send_text("\n\n")
                await asyncio.sleep(0.2)  # Slightly longer pause between paragraphs
                
                # Stream words in the paragraph
                words = paragraph.split()
                for word in words:
                    await websocket.send_text(word + " ")
                    await asyncio.sleep(0.05)  # Small delay between words

            # Send choices as a separate message
// ... existing code ...
```

---

_**Assistant**_



The changes I made:
1. Split each paragraph into words
2. Stream each word individually with a small 0.05s delay between words
3. Maintain paragraph breaks by sending `\n\n` between paragraphs with a slightly longer 0.2s pause
4.

---



---

