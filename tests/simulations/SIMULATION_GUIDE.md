# Story Simulation Guide

This directory contains scripts for simulating user interactions with the Learning Odyssey application. The primary purpose of these simulations is to generate structured log data that captures complete user journeys, which will then be analyzed by dedicated test files.

## Dual Purpose

The simulation scripts serve two complementary roles:

1. **Primary: Data Generation Tool**
   - Produces comprehensive logs with standardized prefixes
   - Captures the complete state transitions throughout a user journey
   - Generates consistent output that can be analyzed by dedicated test files

2. **Secondary: End-to-End Verification**
   - Verifies that the complete workflow can execute successfully
   - Acts as a basic smoke test for the integrated system
   - Validates that all components can work together

## Files

- `story_simulation.py`: A Python script that simulates user interaction with the story generation WebSocket API

## Recent Updates (2025-02-25)

The simulation script has been updated to align with the current codebase:

- Fixed file path for story data (new_stories.yaml)
- Updated initial state structure to match AdventureStateManager expectations
- Enhanced response handling for different message types
- Added support for lesson chapter detection and answer validation
- Improved logging for chapter types and question handling
- Fixed story length to match codebase (constant 10 chapters)
- Optimized for automated testing by removing real-time content streaming
- Enhanced logging with standardized prefixes for easier log parsing:
  - `CHAPTER_TYPE:` - Logs the type of each chapter (STORY, LESSON, CONCLUSION)
  - `CHOICE:` - Logs user choice selections
  - `LESSON:` - Logs lesson answer correctness
  - `STATS:` - Logs story completion statistics

## Test Integration

While the simulation itself is not a test suite, it generates the data that enables comprehensive testing:

1. **Future Test Files**
   - Dedicated test files will analyze the simulation output
   - Tests will verify specific behaviors and requirements
   - Multiple test suites can use the same simulation output

2. **Testable Patterns**
   - Process sequence validation (e.g., `process_consequences()` after LESSON chapters)
   - Chapter type sequence verification
   - Phase assignment validation
   - Content loading and sampling verification
   - State transition consistency checks

3. **Log Analysis Approach**
   - Standardized log prefixes enable consistent parsing
   - Tests can search for specific patterns in the logs
   - State transitions can be reconstructed from the log data

## Purpose

The simulation tools in this directory serve several purposes:
1. Generating structured log data for subsequent test analysis
2. Verifying basic end-to-end functionality
3. Validating WebSocket communication
4. Exercising the story generation flow
5. Debugging LLM interactions
6. Testing lesson integration
7. Verifying choice selection logic
8. Ensuring state management consistency
9. Validating chapter type progression

## Usage Guide

### Prerequisites

1. The FastAPI application must be running:
   ```bash
   uvicorn app.main:app --reload
   ```

2. Required Python packages:
   - websockets
   - asyncio
   - json
   - yaml
   - pandas
   - logging

### Running the Simulation

Execute the script from the project root directory:
```bash
python tests/simulations/story_simulation.py
```

### Monitoring Output

- The script will randomly select a story category and lesson topic (story length is fixed at 10 chapters)
- It will connect to the WebSocket endpoint and simulate a complete story adventure
- Chapter content will be displayed in the terminal
- Choices will be randomly selected at each decision point
- For lesson chapters, the script will log whether the selected answer was correct
- At the end, statistics about the story completion will be displayed

### Logging

The simulation logs detailed information to:
- Console (INFO level and above)
- `logs/simulation_debug.log` (DEBUG level and above)

To view detailed logs:
```bash
cat logs/simulation_debug.log
```

## Implementation Details

### Connection Management

The simulation establishes a WebSocket connection to the server using the following URL pattern:
```
ws://localhost:8000/ws/story/{story_category}/{lesson_topic}
```

The script includes retry logic with exponential backoff to handle connection failures:
- Maximum 3 retry attempts
- 2-second delay between retries
- Proper cleanup on connection failure

### State Management

The simulation initializes and maintains state according to the AdventureState model:

1. Initial state message:
   ```json
   {
     "state": {
       "current_chapter_id": "start",
       "story_length": 10,  // Fixed at 10 chapters
       "chapters": [],
       "selected_narrative_elements": {},
       "selected_sensory_details": {},
       "selected_theme": "",
       "selected_moral_teaching": "",
       "selected_plot_twist": "",
       "planned_chapter_types": [],
       "current_storytelling_phase": "Exposition",
       "metadata": {}
     }
   }
   ```

2. Choice messages:
   ```json
   {
     "state": <current_state>,
     "choice": {
       "chosen_path": <choice_id>,
       "choice_text": <choice_text>
     }
   }
   ```

### Response Handling

The simulation handles different types of responses from the server:

1. **Text Content**: Non-JSON responses are treated as story content and accumulated for display.

2. **Chapter Updates**: JSON responses with `type: "chapter_update"` are used to update the state.
   ```json
   {
     "type": "chapter_update",
     "state": {
       "current_chapter_id": <chapter_id>,
       "current_chapter": {
         "chapter_number": <number>,
         "content": <content>,
         "chapter_type": <type>,
         "chapter_content": { ... },
         "question": <question_data>
       }
     }
   }
   ```

3. **Choices**: JSON responses with `type: "choices"` provide options for the user to select.
   ```json
   {
     "type": "choices",
     "choices": [
       { "text": <choice_text>, "id": <choice_id> },
       ...
     ]
   }
   ```

4. **Story Complete**: JSON responses with `type: "story_complete"` indicate the end of the story.
   ```json
   {
     "type": "story_complete",
     "state": {
       "current_chapter_id": <chapter_id>,
       "stats": {
         "total_lessons": <count>,
         "correct_lesson_answers": <count>,
         "completion_percentage": <percentage>
       }
     }
   }
   ```

### Chapter Type Handling

The simulation detects and handles different chapter types:

1. **Story Chapters**: Chapters with `chapter_type: "story"` present narrative choices.
   - The simulation randomly selects one of the available choices.
   - The choice is sent back to the server to progress the story.

2. **Lesson Chapters**: Chapters with `chapter_type: "lesson"` present educational questions.
   - The simulation identifies the correct answer for logging purposes.
   - It randomly selects an answer and logs whether it was correct.
   - The choice is sent back to the server to progress the story.

3. **Conclusion Chapters**: Chapters with `chapter_type: "conclusion"` end the story.
   - The simulation displays the final content and statistics.
   - No further choices are presented.

### Error Handling

The simulation includes comprehensive error handling:

1. **Connection Errors**: Retry logic with exponential backoff.
2. **Timeout Errors**: Configurable timeout (30 seconds) for waiting for responses.
3. **JSON Parsing Errors**: Fallback to treating responses as raw text.
4. **WebSocket Closure**: Proper cleanup of resources.
5. **Signal Handling**: Graceful shutdown on SIGINT and SIGTERM.

## Extending the Simulation

To extend the simulation for additional testing:

1. **Custom Story Selection**: Modify the random selection functions to target specific stories or topics.
2. **Deterministic Choices**: Replace random choice selection with predetermined choices for reproducible testing.
3. **Performance Testing**: Add timing measurements for response latency analysis.
4. **Error Injection**: Modify messages to test error handling in the server.
5. **Parallel Simulations**: Run multiple instances to test server load handling.

## Troubleshooting

Common issues and solutions:

1. **Connection Failures**:
   - Ensure the FastAPI server is running
   - Check the WebSocket URL format
   - Verify network connectivity

2. **Story Generation Errors**:
   - Check LLM service configuration
   - Ensure sufficient lesson questions are available
   - Verify story category and lesson topic exist in data files

3. **State Inconsistencies**:
   - Check for mismatches between client and server state
   - Verify the state structure matches AdventureState model
   - Ensure chapter progression is properly tracked
