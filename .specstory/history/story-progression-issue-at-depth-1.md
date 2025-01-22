## SpecStory

## Story Progression Issue at Depth=1 (1/22/2025, 9:01:06 PM)

_**User**_

At depth=1, the story begins loading and 3 choices are presented. However, after selecting the choice, the next page is @http://127.0.0.1:8000/story/2 but it's repeating the story at depth=1 again, with the same choices. 

---

_**Assistant**_

Let me help investigate why the story progression isn't working correctly and keeps repeating at depth=1. I'll first look at the relevant code to understand how story progression is handled.

---

_**Assistant**_



---

_**Assistant**_



After reviewing the code, I can see the issue. The problem is in the session state management between page loads. Let me explain what's happening:

1. In `index.html`, when a choice is made, the code correctly:
   - Stores the state in `sessionStorage` (lines 141-149)
   - Increments the depth
   - Navigates to `/story/${depth}`

2. However, when the WebSocket connection is re-established on the new page (lines 169-198), the state is not being properly maintained. The `StoryState` in the WebSocket handler is being reset to initial values:

```python
state = StoryState(
    current_node="start", depth=0, history=[], correct_answers=0, total_questions=0
)
```

Let me fix this by modifying the WebSocket handler to properly maintain the state. I'll edit the `main.py` file:

---

_**Assistant**_

```
@app.websocket("/ws/story/{story_category}/{lesson_topic}")
async def story_websocket(websocket: WebSocket, story_category: str, lesson_topic: str):
    """Handle WebSocket connection for story streaming."""
    await websocket.accept()

    # Initialize with default state
    state = StoryState(
        current_node="start", depth=0, history=[], correct_answers=0, total_questions=0
    )

    try:
        while True:
            data = await websocket.receive_json()
            choice = data.get("choice")
            
            # If we receive a state update, use it to initialize our state
            if "state" in data:
                state = StoryState(
                    current_node=data["state"].get("current_node", "start"),
                    depth=data["state"].get("depth", 0),
                    history=data["state"].get("history", []),
                    correct_answers=data["state"].get("correct_answers", 0),
                    total_questions=data["state"].get("total_questions", 0)
                )
                continue  # Skip to next iteration to wait for choice

            if choice is None:
                continue

            # Only append choice and increment depth for non-state messages
            if choice != "start":  # Don't append "start" to history
                state.history.append(choice)
                state.depth += 1

            try:
                # Generate the complete story node
                story_node = await generate_story_segment(
                    story_category, lesson_topic, state
                )
// ... existing code ...
```

---

_**Assistant**_



Now I'll update the frontend code to send the state when reconnecting:

---

_**Assistant**_

```
// ... existing code ...
                // When connection opens, send the stored choice
                storyWebSocket.onopen = function() {
                    // First send the stored state if it exists
                    const storyState = JSON.parse(sessionStorage.getItem('storyState') || '{}');
                    if (Object.keys(storyState).length > 0) {
                        storyWebSocket.send(JSON.stringify({
                            state: {
                                current_node: storyState.choice,
                                depth: parseInt(sessionStorage.getItem('storyDepth') || '0'),
                                history: storyState.history || [],
                                correct_answers: storyState.correct_answers || 0,
                                total_questions: storyState.total_questions || 0
                            }
                        }));
                    }
                    
                    // Then send the choice to continue the story
                    storyWebSocket.send(JSON.stringify({
                        choice: storyState.choice || 'start'
                    }));
                };
// ... existing code ...
```

---

_**Assistant**_



I also need to update the state storage in the frontend to maintain the history:

---

_**Assistant**_

```
function makeChoice(choiceId) {
    if (storyWebSocket && storyWebSocket.readyState === WebSocket.OPEN) {
        // Get existing state or initialize new one
        const existingState = JSON.parse(sessionStorage.getItem('storyState') || '{}');
        const currentDepth = parseInt(sessionStorage.getItem('storyDepth') || '0');
        
        // Store the current state in sessionStorage
        const currentState = {
            storyCategory: document.getElementById('storyCategory').value,
            lessonTopic: document.getElementById('lessonTopic').value,
            choice: choiceId,
            depth: currentDepth + 1,
            history: [...(existingState.history || []), choiceId],
            correct_answers: existingState.correct_answers || 0,
            total_questions: existingState.total_questions || 0
        };
        
        sessionStorage.setItem('storyState', JSON.stringify(currentState));
        sessionStorage.setItem('storyDepth', currentState.depth.toString());
        
        // Close WebSocket before navigation
        storyWebSocket.close();
        
        // Navigate to the next page
        window.location.href = `/story/${currentState.depth}`;
    }
}
```

---

_**Assistant**_



These changes should fix the story progression issue. Here's what the changes do:

1. The backend WebSocket handler now:
   - Accepts a state update message that initializes the story state
   - Only increments depth and updates history for actual choices (not state updates)

2. The frontend now:
   - Sends the stored state when reconnecting to the WebSocket
   - Properly maintains the choice history in sessionStorage
   - Correctly increments the depth counter

The story should now progress properly through the depths, maintaining the history of choices and not repeating the same depth. When you make a choice:
1. The state is stored with the updated history and depth
2. When the new page loads, it sends this state to the WebSocket
3. The backend uses this state to generate the appropriate next story segment
4. The story continues from where it left off instead of repeating

Try the story again and it should progress properly through the depths without repeating.

---

_**User**_

How about the prompt sent at depth=2? Does it account for the choice made at depth=1?

---

_**Assistant**_

Let me check how the story generation handles choices at depth=2 by looking at the prompt construction and story generation logic.

Looking at `generate_story_segment` in `main.py`, I notice that while we maintain the history of choices in the state, we're not actually using this history when generating the story content. The `question` is only loaded at depth=1, but there's no special handling of the response to that question at depth=2.

Let me modify the code to properly handle the story continuation based on the previous choice:

---

_**Assistant**_

```
async def generate_story_segment(
    story_category: str, lesson_topic: str, state: StoryState
) -> StoryNode:
    """Generate the next story segment based on the current state."""
    # Load story configuration
    story_data = load_story_data()
    story_config = story_data["story_categories"][story_category]

    # Load lesson data if we're at the question depth
    question = None
    previous_answer = None
    
    if state.depth == 1:  # Next node will be depth 2
        lesson_data = load_lesson_data()
        relevant_lessons = lesson_data[lesson_data["topic"] == lesson_topic]
        question = relevant_lessons.iloc[state.total_questions].to_dict()
    elif state.depth == 2 and state.history:  # Handle the response to the previous question
        lesson_data = load_lesson_data()
        relevant_lessons = lesson_data[lesson_data["topic"] == lesson_topic]
        last_question = relevant_lessons.iloc[state.total_questions].to_dict()
        last_choice = state.history[-1]
        
        # Determine if the last answer was correct
        was_correct = last_choice == "correct"
        previous_answer = {
            "question": last_question["question"],
            "chosen_answer": last_question["correct_answer"] if was_correct else 
                           last_question["wrong_answer1"] if last_choice == "wrong1" else 
                           last_question["wrong_answer2"],
            "correct_answer": last_question["correct_answer"],
            "explanation": last_question["explanation"],
            "was_correct": was_correct
        }

    # Generate story content using LLM
    story_stream = await llm_service.generate_story_segment(
        story_config, state, question, previous_answer
    )

    # Process the streaming response
    story_content = ""
    story_choices = []

    try:
        async for chunk in story_stream:
            if chunk.choices[0].delta.content:
                story_content += chunk.choices[0].delta.content
    except Exception as e:
        print(f"Error during story generation: {e}")
        story_content = "I apologize, but I encountered an error generating the story. Please try again."

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
```

---

_**Assistant**_



Now I need to update the LLM service to handle the previous answer information:

---

_**Assistant**_

```
async def generate_story_segment(
        self,
        story_config: Dict[str, Any],
        state: StoryState,
        question: Optional[Dict[str, Any]] = None,
        previous_answer: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Generate the next story segment based on the current state and configuration.

        Args:
            story_config: Configuration for the story category (tone, rules, etc.)
            state: Current story state including history
            question: Optional educational question to integrate
            previous_answer: Optional information about the previous question's answer
        """
        # Build the system prompt that establishes the storytelling framework
        system_prompt = self._build_system_prompt(story_config)

        # Build the user prompt that includes story state and requirements
        user_prompt = self._build_user_prompt(story_config, state, question, previous_answer)

        # Debug output
        print("\n=== DEBUG: LLM Request ===")
        print("System Prompt:")
        print(system_prompt)
        print("\nUser Prompt:")
        print(user_prompt)
        print("========================\n")

        try:
            # Call the LLM with our prompts
            response = await self.client.chat.completions.create(
                model="gpt-4-0125-preview",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,  # Balanced between creativity and consistency
                stream=True,  # Enable streaming for real-time story delivery
            )
            return response
        except Exception as e:
            print(f"\n=== ERROR: LLM Request Failed ===")
            print(f"Error type: {type(e).__name__}")
            print(f"Error message: {str(e)}")
            print("===============================\n")
            raise  # Re-raise the exception after logging

    def _build_user_prompt(
        self,
        story_config: Dict[str, Any],
        state: StoryState,
        question: Optional[Dict[str, Any]],
        previous_answer: Optional[Dict[str, Any]],
    ) -> str:
        """Create a user prompt that includes story state and current requirements."""
        prompt = f"""Current story state:
- Depth: {state.depth} of 3
- Previous choices: {", ".join(state.history) if state.history else "Story beginning"}

"""

        if state.depth == 0:
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
        elif previous_answer:
            # Handle the response to the previous question
            prompt += f"""Continue the story, acknowledging the character's previous answer to the question: "{previous_answer["question"]}"

They chose: "{previous_answer["chosen_answer"]}"
This was {"correct" if previous_answer["was_correct"] else "incorrect"}. 
The correct answer was: "{previous_answer["correct_answer"]}"
Explanation: {previous_answer["explanation"]}

Incorporate this information naturally into the story, providing:
1. A response that acknowledges whether they were correct or incorrect
2. A natural way to explain why this was the right/wrong answer
3. Use this as a learning moment that moves the story forward
4. End with two meaningful choices for how to proceed with the adventure

The explanation should feel like a natural part of the story rather than a direct educational message."""
        else:
            # Regular story continuation
            prompt += """Continue the story based on the previous choices, 
            creating meaningful consequences for the character's decisions.
            
End this segment with two clear choices that would lead the story in different directions."""

        return prompt
```

---

_**Assistant**_



These changes will now properly handle the story progression at depth=2 by:

1. Tracking whether the previous answer was correct or incorrect
2. Including the full context of the previous question and answer
3. Providing the explanation for why the answer was right/wrong
4. Incorporating this information naturally into the story continuation

The story at depth=2 will now:
- Acknowledge the player's previous choice
- Explain why their answer was correct or incorrect in a story-appropriate way
- Use this as a learning moment
- Continue the story with meaningful choices that build on this understanding

Try the story again and you should see that at depth=2, the story properly responds to and builds upon your choice from depth=1, rather than just continuing without acknowledging the previous answer.

---

_**User**_

The questions and choices at depth=1 are not coming from `lessons.csv`. 

---

_**Assistant**_

Let me check how the questions are being loaded and used. Looking at the code, I see that we're trying to load questions from `lessons.csv`, but we should verify if the data is being loaded correctly and if we're accessing the right rows.

---

_**Assistant**_



---

_**Assistant**_



I see the issue. Let's look at how we're accessing the lesson data in the code:

---

_**Assistant**_



---

_**Assistant**_



I see the issue. In `generate_story_segment`, we're trying to load the lesson data but not properly handling the case where there are no matching lessons for the topic. Let me fix this:

---

_**Assistant**_

```
async def generate_story_segment(
    story_category: str, lesson_topic: str, state: StoryState
) -> StoryNode:
    """Generate the next story segment based on the current state."""
    # Load story configuration
    story_data = load_story_data()
    story_config = story_data["story_categories"][story_category]

    # Load lesson data if we're at the question depth
    question = None
    previous_answer = None

    if state.depth == 1:  # Next node will be depth 2
        lesson_data = load_lesson_data()
        relevant_lessons = lesson_data[lesson_data["topic"] == lesson_topic]
        
        if len(relevant_lessons) > 0:
            question = relevant_lessons.iloc[state.total_questions % len(relevant_lessons)].to_dict()
            print(f"Loaded question for topic {lesson_topic}: {question}")
        else:
            print(f"No lessons found for topic {lesson_topic}")
            # Fallback to generic choices if no lessons available
            return StoryNode(
                content="As your adventure continues, you face a choice...",
                choices=[
                    StoryChoice(text="Continue with caution", next_node="node_1_0"),
                    StoryChoice(text="Take a bold approach", next_node="node_1_1"),
                ]
            )
            
    elif state.depth == 2 and state.history:  # Handle the response to the previous question
        lesson_data = load_lesson_data()
        relevant_lessons = lesson_data[lesson_data["topic"] == lesson_topic]
        
        if len(relevant_lessons) > 0:
            last_question = relevant_lessons.iloc[state.total_questions % len(relevant_lessons)].to_dict()
            last_choice = state.history[-1]

            # Determine if the last answer was correct
            was_correct = last_choice == "correct"
            previous_answer = {
                "question": last_question["question"],
                "chosen_answer": last_question["correct_answer"] if was_correct 
                               else last_question["wrong_answer1"] if last_choice == "wrong1"
                               else last_question["wrong_answer2"],
                "correct_answer": last_question["correct_answer"],
                "explanation": last_question["explanation"],
                "was_correct": was_correct,
            }

    # Generate story content using LLM
    story_stream = await llm_service.generate_story_segment(
        story_config, state, question, previous_answer
    )

    # Process the streaming response
    story_content = ""
    story_choices = []

    try:
        async for chunk in story_stream:
            if chunk.choices[0].delta.content:
                story_content += chunk.choices[0].delta.content
    except Exception as e:
        print(f"Error during story generation: {e}")
        story_content = "I apologize, but I encountered an error generating the story. Please try again."

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
```

---

_**Assistant**_







Now let me check if the lessons are being loaded correctly at startup:

---

_**Assistant**_

```
python -c "from app.main import load_lesson_data; print(load_lesson_data())"
```

---

_**Assistant**_



The lessons are being loaded correctly from the CSV file. Let me check what topics are available:

---

_**Assistant**_

```
python -c "from app.main import load_lesson_data; print(load_lesson_data()['topic'].unique())"
```

---

_**Assistant**_

```
python -c "from app.main import load_lesson_data; df = load_lesson_data(); print('Available topics:', df['topic'].unique())"
```

---

_**Assistant**_



I see the issue now. The available topics are 'Singapore History', 'Human Body', and 'Farm Animals'. The problem is likely that you're selecting a topic that doesn't match these exactly. Let me add some debug logging to see what topic is being selected:

---

_**Assistant**_

```
async def generate_story_segment(
    story_category: str, lesson_topic: str, state: StoryState
) -> StoryNode:
    """Generate the next story segment based on the current state."""
    # Load story configuration
    story_data = load_story_data()
    story_config = story_data["story_categories"][story_category]

    # Load lesson data if we're at the question depth
    question = None
    previous_answer = None

    if state.depth == 1:  # Next node will be depth 2
        lesson_data = load_lesson_data()
        print(f"\nDEBUG: Available topics: {lesson_data['topic'].unique()}")
        print(f"DEBUG: Selected topic: '{lesson_topic}'")
        
        relevant_lessons = lesson_data[lesson_data["topic"] == lesson_topic]
        print(f"DEBUG: Found {len(relevant_lessons)} lessons for topic {lesson_topic}")
        
        if len(relevant_lessons) > 0:
            question = relevant_lessons.iloc[state.total_questions % len(relevant_lessons)].to_dict()
            print(f"DEBUG: Loaded question: {question['question']}")
            print(f"DEBUG: Choices: {question['correct_answer']}, {question['wrong_answer1']}, {question['wrong_answer2']}")
        else:
            print(f"WARNING: No lessons found for topic '{lesson_topic}'")
            # Fallback to generic choices if no lessons available
            return StoryNode(
                content="As your adventure continues, you face a choice...",
                choices=[
                    StoryChoice(text="Continue with caution", next_node="node_1_0"),
                    StoryChoice(text="Take a bold approach", next_node="node_1_1"),
                ]
            )
            
    elif state.depth == 2 and state.history:  # Handle the response to the previous question
        lesson_data = load_lesson_data()
        relevant_lessons = lesson_data[lesson_data["topic"] == lesson_topic]
        
        if len(relevant_lessons) > 0:
            last_question = relevant_lessons.iloc[state.total_questions % len(relevant_lessons)].to_dict()
            last_choice = state.history[-1]

            # Determine if the last answer was correct
            was_correct = last_choice == "correct"
            previous_answer = {
                "question": last_question["question"],
                "chosen_answer": last_question["correct_answer"] if was_correct 
                               else last_question["wrong_answer1"] if last_choice == "wrong1"
                               else last_question["wrong_answer2"],
                "correct_answer": last_question["correct_answer"],
                "explanation": last_question["explanation"],
                "was_correct": was_correct,
            }
            print(f"DEBUG: Processing previous answer. Was correct: {was_correct}")

    # Generate story content using LLM
    story_stream = await llm_service.generate_story_segment(
        story_config, state, question, previous_answer
    )
```

---

_**Assistant**_







Now try running the story again and select one of these exact topics:
- Singapore History
- Human Body
- Farm Animals

The issue was that the topic matching is case-sensitive and exact. When you select a topic, it needs to match one of these exactly. The debug logging I added will help us see if there's any mismatch between the selected topic and the available topics.

Let me also modify the frontend to ensure the topics are displayed exactly as they appear in the CSV:

---

_**Assistant**_

```
                    <select id="lessonTopic" name="lessonTopic" required
                            class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500">
                        <option value="">Select a topic...</option>
                        {% for topic in lesson_topics %}
                        <option value="{{ topic }}">{{ topic }}</option>
                        {% endfor %}
                    </select>
```

---

_**Assistant**_



I see that the template was already correct. The issue must be with the topic selection. When you run the story again:

1. Make sure to select one of these exact topics:
   - Singapore History
   - Human Body
   - Farm Animals

2. The debug output I added will show:
   - The available topics
   - The topic you selected
   - How many lessons were found
   - The question and choices that were loaded

This will help us confirm that the topic matching is working correctly and that the questions are being loaded from the CSV file.

---

_**User**_

This is the output at depth=1 after selecting "Singapore History" as the lesson : 

```
In a world where the whispers of the wind speak of ancient magic and the stars guide those worthy of their secrets, there lies an enchanted forest. This forest, known to the few who dare enter as the Sylvan Glade, is home to creatures of myth and legend. It is here, under the canopy of whispering leaves and glowing lanterns strung from the branches of ageless trees, that our tale begins. 

Our protagonist, a young wizard named Elior, had always been fascinated by the magic that coursed through the veins of the Sylvan Glade. Elior, with a heart as curious as the path that wound through the forest, had just turned the age when tradition allowed for the beginning of a magical education. With a mop of unruly hair that seemed to have its own magical properties and eyes as bright as the constellation-filled sky above, Elior was eager to start this journey. 

On the morning that would mark the beginning of a new chapter, Elior stood at the edge of the forest, the early light casting golden hues through the trees, making the dewdrops sparkle like tiny stars. Behind, lay the familiar comfort of home, a quaint cottage filled with the scent of old books and the warmth of crackling firewood. Ahead, the unknown awaited, promising adventure and the fulfillment of a dream nurtured since childhood. 

Elior's first steps into the forest felt like crossing into another world. The air buzzed with magic, and the ground seemed to pulse with life underfoot. It wasn't long before Elior reached a clearing where the sunlight danced upon a peculiar sight—a school like no other. This was the Arcanum, a place of learning for those gifted in the magical arts. Its walls were entwined with vines that shimmered with an ethereal glow, and its windows gazed out like wise eyes, reflecting the world in a myriad of colors. 

As Elior approached the grand entrance, a sense of destiny filled the air. Today, Elior would not only learn about magic but also embark on a journey of self-discovery, facing challenges that would require more than spells to overcome. 

The Arcanum's doors stood open, as if welcoming Elior personally into its halls. Taking a deep breath, Elior stepped inside, ready to meet whatever the future held. 

The choice now before Elior was where to begin this adventure in magical learning. To the left, a corridor led to the Crystal Caves, where students learned the secrets of the earth and the crystals that pulsed with the world's heartbeat. To the right, a pathway opened to the Enchanted Forest, a place for mastering the arts of nature and understanding the language of the creatures that called it home. 

Where should Elior begin? 

1. Explore the Crystal Caves and learn the secrets of the earth. 2. Venture into the Enchanted Forest to master the arts of nature. 
```

The question at the end should be pulled out from the database, and not self generated.


---

_**Assistant**_

Ah, I see the issue now. The LLM is generating its own story choices instead of using the questions from the database. Looking at the code, the problem is in the order of operations. We're generating the story content first, and then trying to add the choices afterward.

Let me modify the code to ensure we use the database questions:

---

_**Assistant**_

```
async def generate_story_segment(
    story_category: str, lesson_topic: str, state: StoryState
) -> StoryNode:
    """Generate the next story segment based on the current state."""
    # Load story configuration
    story_data = load_story_data()
    story_config = story_data["story_categories"][story_category]

    # Load lesson data if we're at the question depth
    question = None
    previous_answer = None

    if state.depth == 1:  # Next node will be depth 2
        lesson_data = load_lesson_data()
        print(f"\nDEBUG: Available topics: {lesson_data['topic'].unique()}")
        print(f"DEBUG: Selected topic: '{lesson_topic}'")

        relevant_lessons = lesson_data[lesson_data["topic"] == lesson_topic]
        print(f"DEBUG: Found {len(relevant_lessons)} lessons for topic {lesson_topic}")

        if len(relevant_lessons) > 0:
            question = relevant_lessons.iloc[
                state.total_questions % len(relevant_lessons)
            ].to_dict()
            print(f"DEBUG: Loaded question: {question['question']}")
            print(
                f"DEBUG: Choices: {question['correct_answer']}, {question['wrong_answer1']}, {question['wrong_answer2']}"
            )
            
            # Generate story content using LLM
            story_stream = await llm_service.generate_story_segment(
                story_config, state, question, previous_answer
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

            # Use the database question choices
            story_choices = [
                StoryChoice(text=question["correct_answer"], next_node="correct"),
                StoryChoice(text=question["wrong_answer1"], next_node="wrong1"),
                StoryChoice(text=question["wrong_answer2"], next_node="wrong2"),
            ]
            
            return StoryNode(content=story_content, choices=story_choices)
        else:
            print(f"WARNING: No lessons found for topic '{lesson_topic}'")
            # Fallback to generic choices if no lessons available
            return StoryNode(
                content="As your adventure continues, you face a choice...",
                choices=[
                    StoryChoice(text="Continue with caution", next_node="node_1_0"),
                    StoryChoice(text="Take a bold approach", next_node="node_1_1"),
                ],
            )

    elif state.depth == 2 and state.history:  # Handle the response to the previous question
        lesson_data = load_lesson_data()
        relevant_lessons = lesson_data[lesson_data["topic"] == lesson_topic]

        if len(relevant_lessons) > 0:
            last_question = relevant_lessons.iloc[
                state.total_questions % len(relevant_lessons)
            ].to_dict()
            last_choice = state.history[-1]

            # Determine if the last answer was correct
            was_correct = last_choice == "correct"
            previous_answer = {
                "question": last_question["question"],
                "chosen_answer": last_question["correct_answer"]
                if was_correct
                else last_question["wrong_answer1"]
                if last_choice == "wrong1"
                else last_question["wrong_answer2"],
                "correct_answer": last_question["correct_answer"],
                "explanation": last_question["explanation"],
                "was_correct": was_correct,
            }
            print(f"DEBUG: Processing previous answer. Was correct: {was_correct}")

    # Generate story content using LLM
    story_stream = await llm_service.generate_story_segment(
        story_config, state, question, previous_answer
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

    # For non-question nodes, use generic choices
    story_choices = [
        StoryChoice(text=f"Choice {i + 1}", next_node=f"node_{state.depth}_{i}")
        for i in range(2)
    ]

    return StoryNode(content=story_content, choices=story_choices)
```

---

_**Assistant**_







Let me also update the LLM service to ensure it properly integrates the question into the story:

---

_**Assistant**_

```
    def _build_user_prompt(
        self,
        story_config: Dict[str, Any],
        state: StoryState,
        question: Optional[Dict[str, Any]],
        previous_answer: Optional[Dict[str, Any]],
    ) -> str:
        """Create a user prompt that includes story state and current requirements."""
        prompt = f"""Current story state:
- Depth: {state.depth} of 3
- Previous choices: {", ".join(state.history) if state.history else "Story beginning"}

"""

        if state.depth == 0:
            prompt += "Generate the opening scene of the story, introducing the setting and main character."
        elif question:
            # Integrate educational question naturally into the story
            prompt += f"""Continue the story, naturally leading to a situation where the following question needs to be answered: "{question["question"]}"

The character will have three possible responses:
1. {question["correct_answer"]}
2. {question["wrong_answer1"]}
3. {question["wrong_answer2"]}

Important:
1. Build up the story naturally to this specific question
2. Do not invent or add any other choices
3. End by presenting the exact question and these three choices
4. Make sure the question feels like a natural part of the story's progression
5. Do not include any hints about which answer might be correct"""
        elif previous_answer:
            # Handle the response to the previous question
            prompt += f"""Continue the story, acknowledging the character's previous answer to the question: "{previous_answer["question"]}"

They chose: "{previous_answer["chosen_answer"]}"
This was {"correct" if previous_answer["was_correct"] else "incorrect"}. 
The correct answer was: "{previous_answer["correct_answer"]}"
Explanation: {previous_answer["explanation"]}

Incorporate this information naturally into the story, providing:
1. A response that acknowledges whether they were correct or incorrect
2. A natural way to explain why this was the right/wrong answer
3. Use this as a learning moment that moves the story forward
4. End with two meaningful choices for how to proceed with the adventure

The explanation should feel like a natural part of the story rather than a direct educational message."""
        else:
            # Regular story continuation
            prompt += """Continue the story based on the previous choices, 
            creating meaningful consequences for the character's decisions.
            
End this segment with two clear choices that would lead the story in different directions."""

        return prompt
```

---

_**Assistant**_







These changes should fix the issue:

1. The story generation logic has been restructured to:
   - First load the question from the database
   - Then generate a story that leads to that specific question
   - Use the exact choices from the database

2. The LLM prompt has been updated to:
   - Explicitly require using the exact question from the database
   - Not add any additional choices
   - Not provide hints about the correct answer
   - Present the choices exactly as they appear in the database

Try running the story again with "Singapore History" as the topic. You should now see:
1. A story that naturally leads to one of the Singapore History questions from the database
2. The exact choices from the database presented at the end
3. No additional or made-up choices

The debug output will also show you which question and choices were loaded from the database, so you can verify they match what appears in the story.

---

_**User**_

It's still not asking questions about Singapore History (selected choice) at depth=1.

---

_**Assistant**_

Let me check the flow more carefully. The issue might be that we're not properly handling the state.depth in relation to when we should present the question.

---

_**Assistant**_

```
async def generate_story_segment(
    story_category: str, lesson_topic: str, state: StoryState
) -> StoryNode:
    """Generate the next story segment based on the current state."""
    print(f"\nDEBUG: Current state - depth: {state.depth}, history: {state.history}")
    
    # Load story configuration
    story_data = load_story_data()
    story_config = story_data["story_categories"][story_category]

    # Load lesson data if we're at the question depth
    question = None
    previous_answer = None

    # At depth 0, we show the opening scene
    if state.depth == 0:
        story_stream = await llm_service.generate_story_segment(
            story_config, state, question, previous_answer
        )
        story_content = ""
        try:
            async for chunk in story_stream:
                if chunk.choices[0].delta.content:
                    story_content += chunk.choices[0].delta.content
        except Exception as e:
            print(f"Error during story generation: {e}")
            story_content = "I apologize, but I encountered an error generating the story. Please try again."

        # For opening scene, use generic choices
        story_choices = [
            StoryChoice(text=f"Choice {i + 1}", next_node=f"node_0_{i}")
            for i in range(2)
        ]
        return StoryNode(content=story_content, choices=story_choices)

    # At depth 1, we present the educational question
    elif state.depth == 1:
        lesson_data = load_lesson_data()
        print(f"\nDEBUG: Available topics: {lesson_data['topic'].unique()}")
        print(f"DEBUG: Selected topic: '{lesson_topic}'")

        relevant_lessons = lesson_data[lesson_data["topic"] == lesson_topic]
        print(f"DEBUG: Found {len(relevant_lessons)} lessons for topic {lesson_topic}")

        if len(relevant_lessons) > 0:
            question = relevant_lessons.iloc[
                state.total_questions % len(relevant_lessons)
            ].to_dict()
            print(f"DEBUG: Loaded question: {question['question']}")
            print(
                f"DEBUG: Choices: {question['correct_answer']}, {question['wrong_answer1']}, {question['wrong_answer2']}"
            )

            # Generate story content using LLM
            story_stream = await llm_service.generate_story_segment(
                story_config, state, question, previous_answer
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

            # Use the database question choices
            story_choices = [
                StoryChoice(text=question["correct_answer"], next_node="correct"),
                StoryChoice(text=question["wrong_answer1"], next_node="wrong1"),
                StoryChoice(text=question["wrong_answer2"], next_node="wrong2"),
            ]

            return StoryNode(content=story_content, choices=story_choices)
        else:
            print(f"WARNING: No lessons found for topic '{lesson_topic}'")
            return StoryNode(
                content="As your adventure continues, you face a choice...",
                choices=[
                    StoryChoice(text="Continue with caution", next_node="node_1_0"),
                    StoryChoice(text="Take a bold approach", next_node="node_1_1"),
                ],
            )

    # At depth 2, we handle the response to the previous question
    elif state.depth == 2:
        lesson_data = load_lesson_data()
        relevant_lessons = lesson_data[lesson_data["topic"] == lesson_topic]
        
        if len(relevant_lessons) > 0 and state.history:
            last_question = relevant_lessons.iloc[
                state.total_questions % len(relevant_lessons)
            ].to_dict()
            last_choice = state.history[-1]

            # Determine if the last answer was correct
            was_correct = last_choice == "correct"
            previous_answer = {
                "question": last_question["question"],
                "chosen_answer": last_question["correct_answer"]
                if was_correct
                else last_question["wrong_answer1"]
                if last_choice == "wrong1"
                else last_question["wrong_answer2"],
                "correct_answer": last_question["correct_answer"],
                "explanation": last_question["explanation"],
                "was_correct": was_correct,
            }
            print(f"DEBUG: Processing previous answer. Was correct: {was_correct}")

            # Generate story content using LLM
            story_stream = await llm_service.generate_story_segment(
                story_config, state, question, previous_answer
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

            # For depth 2, use generic choices for the next step
            story_choices = [
                StoryChoice(text=f"Choice {i + 1}", next_node=f"node_2_{i}")
                for i in range(2)
            ]

            return StoryNode(content=story_content, choices=story_choices)

    # Default case (shouldn't happen with depth validation)
    return StoryNode(
        content="The story has reached its conclusion.",
        choices=[StoryChoice(text="Start Over", next_node="start")]
    )
```

---

_**Assistant**_







I've completely restructured the story generation to be more explicit about what happens at each depth:

1. At depth=0 (start):
   - Generate opening scene
   - Present generic choices to begin the adventure

2. At depth=1:
   - Load the question from the database for the selected topic
   - Generate a story that leads to that question
   - Present the exact choices from the database

3. At depth=2:
   - Process the previous answer
   - Generate feedback based on whether they were correct
   - Present generic choices for the next step

I've also added more debug logging to help us track the state. When you run the story now:

1. Select "Singapore History" as the topic
2. At depth=1, you should see debug output showing:
   - The current depth and history
   - The available topics
   - The selected topic
   - The question and choices loaded from the database

The story should now properly incorporate the Singapore History question at depth=1. Let me know if you're still not seeing the correct questions, and we can check the debug output to see what's happening.

---

_**User**_

I want to to reset all chances to my last commit.

---

_**Assistant**_



---



---

