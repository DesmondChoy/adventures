## Plan: Python Script to Simulate User Journey and Capture Debug Output

> **Note:** This script has already been implemented as `story_simulation.py` and is located in the `tests/simulations` directory. This document serves as a reference for the implementation details and usage instructions.

**Objective:** Create a Python script that simulates a user interacting with the "Learning Odyssey" app via WebSocket to generate chapters, capturing debug output (LLM prompts and responses) for analysis.

**Prerequisites:**

1. **Virtual Environment:**
   ```powershell
   # Windows PowerShell
   .\.venv\Scripts\activate  # Activate virtual environment
   ```
   The virtual environment must be activated before running either the FastAPI application or the simulation script.

2. **Required Libraries:**
   The following libraries should be installed in your virtual environment:
   - `websockets`
   - `pandas`
   - `PyYAML`
   These are included in the project's `requirements.txt`.

3. **FastAPI Application:**
   The FastAPI application must be running locally:
   ```bash
   uvicorn app.main:app --reload
   ```

**Directory Structure:**
```
tests/
├── __init__.py
├── test_prompt_engineering.py
├── test_story_generation.py
└── simulations/
    ├── README.md
    ├── simulation_plan.md
    └── story_simulation.py
```

**Implementation Details:**

1.  **Import Libraries:**
    ```python
    import asyncio
    import websockets
    import json
    import random
    import yaml
    import pandas as pd
    import logging
    import urllib.parse
    ```

2.  **Configure Logging:**
    ```python
    # Configure Logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    # Configure websockets logger to only show warnings and errors
    logging.getLogger('websockets').setLevel(logging.WARNING)
    logger = logging.getLogger(__name__)
    ```

3.  **Helper Functions:**
    ```python
    def print_separator(title=""):
        """Print a visual separator with optional title."""
        width = 80
        if title:
            padding = (width - len(title) - 2) // 2
            print("\n" + "=" * padding + f" {title} " + "=" * padding)
        else:
            print("\n" + "=" * width)

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
        story_lengths = [3, 5, 7]  # Mirror available options in index.html
        return random.choice(story_lengths)
    ```

4.  **Main Simulation Function:**
    The `simulate_story()` async function handles:
    - Loading story and lesson data
    - Random selection of story parameters
    - WebSocket connection and message handling
    - Story content streaming and display
    - Choice selection logic
    - Error handling

5.  **WebSocket Message Handling:**
    The script handles three types of messages:
    - Text streaming (story content)
    - JSON messages (chapter updates and choices)
    - Story completion messages

6.  **Choice Selection Logic:**
    ```python
    # For lesson chapters, always pick the first choice (assumed to be correct)
    if response_data["state"]["current_chapter"].get("chapter_type") == "lesson":
        chosen_choice = choices_data[0]
    else:
        # For story chapters, pick randomly
        chosen_choice = random.choice(choices_data)
    ```

7.  **Output Formatting:**
    The script uses visual separators and organized sections:
    ```
    ============================= Story Configuration =============================
    Category: animal_adventures
    Topic: Human Body
    Length: 3 chapters

    ============================== Chapter Content ==============================
    [Story content displayed here]

    ================================ Choices =================================
    1. Choice A (ID: choice_a)
    2. Choice B (ID: choice_b)
    3. Choice C (ID: choice_c)
    ```

**Error Handling:**
- WebSocket connection errors
- JSON parsing errors
- File loading errors
- Unexpected server responses

**Usage:**
1. Ensure you're in the project root directory:
   ```powershell
   cd path\to\coya_app_2025
   ```

2. Activate the virtual environment:
   ```powershell
   .\.venv\Scripts\activate
   ```

3. Start the FastAPI application in one terminal:
   ```bash
   uvicorn app.main:app --reload
   ```

4. Run the simulation script in another terminal (with virtual environment activated):
   ```bash
   python tests/simulations/story_simulation.py
   ```

**Key Features:**
1. Automatic random selection of story parameters
2. Real-time streaming of story content
3. Intelligent choice selection (first choice for lessons, random for stories)
4. Clear, formatted output with visual separators
5. Comprehensive error handling
6. Proper WebSocket message handling
7. URL encoding of parameters

**Output:**
The script provides:
- Story configuration details
- Streamed story content
- Available choices
- Selected choices
- Story completion statistics
- Error messages (if any)

This simulation script provides a robust foundation for testing and debugging the "Learning Odyssey" application's story generation flow. The logging strategy aligns with the application's existing structured logging approach, making it easier to analyze the interaction between the simulation client and the server.
