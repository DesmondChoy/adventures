## Plan: Python Script to Simulate User Journey and Capture Debug Output

**Objective:** Create a Python script that simulates a user interacting with the "Learning Odyssey" app via WebSocket to generate four chapters, capturing debug output (LLM prompts and responses) for analysis.

**Assumptions:**

*   Your FastAPI application (`uvicorn app.main:app --reload`) is running locally.
*   You have activated the Python virtual environment (`.venv`) which already contains the necessary libraries (`websockets`, `pandas`, `PyYAML`).
*   You want to focus on debugging the LLM interactions and prompt flow, not necessarily a perfect end-to-end user simulation.

**Steps:**

1.  **Import Libraries:**
    Start by importing the necessary Python libraries at the beginning of your script:

    ```python
    import asyncio
    import websockets
    import json
    import random
    import yaml
    import pandas as pd
    import logging
    ```

2.  **Configure Logging:**
    Set up logging to match the application's structured logging approach. This will ensure consistency with the app's logging strategy:

    ```python
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    ```

3.  **Load Story and Lesson Data:**
    Mimic how your web app loads story categories and lesson topics. Adapt the loading functions from your `app/routers/web.py` or `app/init_data.py`:

    ```python
    def load_story_data():
        """Load story data from YAML file."""
        try:
            with open("app/data/stories.yaml", "r") as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to load story data: {e}")
            return {"story_categories": {}}

    def load_lesson_data():
        """Load lesson data from CSV file."""
        try:
            return pd.read_csv("app/data/lessons.csv")
        except Exception as e:
            logger.error(f"Failed to load lesson data: {e}")
            return pd.DataFrame(columns=["topic"])

    story_data = load_story_data()
    lesson_df = load_lesson_data()
    ```

4.  **Random Selection Functions:**
    Create functions to randomly select story category, lesson topic, and story length, mirroring the user choices on the landing page:

    ```python
    def get_random_story_category(story_data):
        """Randomly select a story category."""
        categories = list(story_data["story_categories"].keys())
        return random.choice(categories)

    def get_random_lesson_topic(lesson_df):
        """Randomly select a lesson topic."""
        topics = lesson_df["topic"].unique()
        return random.choice(topics)

    def get_random_story_length():
        """Randomly select a story length."""
        story_lengths = [3, 5, 7] # Mirror available options in index.html
        return random.choice(story_lengths)
    ```

5.  **Select Random Options:**
    Use the functions to make random selections for the simulated user:

    ```python
    story_category = get_random_story_category(story_data)
    lesson_topic = get_random_lesson_topic(lesson_df)
    story_length = get_random_story_length()

    logger.info(f"Simulated user selected: Category='{story_category}', Topic='{lesson_topic}', Length={story_length} chapters")
    ```

6.  **LLM Debug Output:**
    The application's LLM services (`OpenAIService` and `GeminiService`) already include comprehensive logging. The `OpenAIService` uses structured logging with the following information:
    - LLM Prompt Request: System and user prompts
    - LLM Response: Complete response content
    - Error logging: Error type, message, and original prompts

    No modifications are needed as the logging is already properly configured to capture:
    - System and user prompts
    - Complete responses
    - Error information with context

7.  **Establish WebSocket Connection and Initial Message:**
    Connect to the WebSocket endpoint using `websockets` and send the initial "start" message with the selected story length:

    ```python
    async def simulate_story():
        uri = f"ws://localhost:8000/ws/story/{story_category}/{lesson_topic}" # Adjust host/port if needed

        async with websockets.connect(uri) as websocket:
            logger.info("WebSocket connection established.")

            # Send initial state message with story length
            initial_state_message = {
                "state": {
                    "current_chapter_id": "start",
                    "current_chapter_number": 0,
                    "story_choices": [],
                    "correct_lesson_answers": 0,
                    "total_lessons": 0,
                    "previous_chapter_content": "",
                    "story_length": story_length
                }
            }
            await websocket.send(json.dumps(initial_state_message))
            logger.debug(f"Sent initial state: {initial_state_message}")

            # Send 'start' choice to begin story
            start_choice_message = {"choice": "start"}
            await websocket.send(json.dumps(start_choice_message))
            logger.debug(f"Sent start choice: {start_choice_message}")

            # Chapter generation loop (4 chapters) - see next step

    if __name__ == "__main__":
        asyncio.run(simulate_story())
    ```

8.  **Chapter Generation Loop:**
    Implement a loop that runs for four chapters. Inside the loop, receive chapter data, simulate a choice, and send the choice back to the server:

    ```python
    async def simulate_story():
        # ... (WebSocket connection and initial message from step 7) ...

        for chapter_num in range(1, 5): # Generate 4 chapters
            logger.info(f"\n========== Chapter {chapter_num} ==========")

            try:
                # Receive chapter update (content and choices)
                response_json = await websocket.recv()
                response_data = json.loads(response_json)
                logger.debug(f"Received message: {response_data.get('type')}")

                if response_data.get('type') == 'chapter_update':
                    chapter_content = response_data['state']['current_chapter']['chapter_content']['content']
                    choices_data = response_data.get('choices')
                    if not choices_data:
                        choices_data_json = await websocket.recv() # Wait for choices message if separate
                        choices_data = json.loads(choices_data_json).get('choices')

                    print("\n===== Chapter Content ======")
                    print(chapter_content) # Print chapter content to console

                    if choices_data:
                        print("\n===== Choices ======")
                        for i, choice in enumerate(choices_data):
                            print(f"  {i+1}. {choice['text']} (ID: {choice['id']})")

                        # Simulate choice selection (randomly for story, 'correct' for lesson - simplified)
                        if response_data['state']['current_chapter']['chapter_type'] == 'lesson':
                            chosen_choice = choices_data[0] # For lesson, pick first choice
                            logger.info(f"Simulating LESSON choice: '{chosen_choice['text']}' (ID: {chosen_choice['id']})")
                        else: # Story chapter
                            chosen_choice = random.choice(choices_data)
                            logger.info(f"Simulating STORY choice: '{chosen_choice['text']}' (ID: {chosen_choice['id']})")

                        choice_message = {
                            "choice": {
                                "chosen_path": chosen_choice['id'],
                                "choice_text": chosen_choice['text']
                            }
                        }
                        await websocket.send(json.dumps(choice_message))
                        logger.debug(f"Sent choice: {choice_message}")

                elif response_data.get('type') == 'story_complete':
                    logger.info("\nStory completed successfully!")
                    stats = response_data['state']['stats']
                    print("\n===== Story Stats =====")
                    print(f"  Total Lessons: {stats['total_lessons']}")
                    print(f"  Correct Answers: {stats['correct_lesson_answers']}")
                    print(f"  Success Rate: {stats['completion_percentage']}%")
                    break

            except websockets.exceptions.ConnectionClosed:
                logger.error("WebSocket connection closed unexpectedly")
                break
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON message: {e}")
                break
            except Exception as e:
                logger.error(f"Unexpected error during chapter simulation: {e}")
                break

        logger.info("Simulation finished.")
    ```

9.  **Run the Script and Analyze Output:**

    *   **Ensure your FastAPI application is running:** `uvicorn app.main:app --reload` in your terminal.
    *   **Activate the virtual environment:** Activate your Python virtual environment using the appropriate command for your OS.
    *   **Run your Python simulation script:** `python story_simulation.py`
    *   **Observe the output in your terminal:**
        *   Script logs (INFO, DEBUG messages)
        *   LLM prompts and responses through the application's structured logging
        *   Chapter content and choices printed by the script
        *   Any error messages or unexpected behaviors

**Important Considerations and Debugging Tips:**

*   **Error Handling:** The script includes robust error handling with proper logging for WebSocket operations, JSON parsing, and general exceptions.
*   **Logging Levels:** Adjust the logging level in your script (`logging.basicConfig(level=...)`) to control output verbosity. Use `logging.DEBUG` for more detailed information.
*   **Server Logs:** The FastAPI application logs to `logs/app.log`. Check this file alongside the simulation output for a complete picture of the interaction flow.
*   **Choice Simulation:** The choice simulation is simplified. Consider enhancing it for more realistic testing (e.g., weighting choices, simulating incorrect lesson answers).
*   **Asynchronous Nature:** The script properly handles the asynchronous WebSocket communication using `async`/`await`.
*   **JSON Handling:** The script includes proper JSON encoding/decoding with error handling for WebSocket messages.

This simulation script provides a solid foundation for testing and debugging your "Learning Odyssey" application's story generation flow. The logging strategy aligns with the application's existing structured logging approach, making it easier to analyze the interaction between the simulation client and the server.
