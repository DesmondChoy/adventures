# Testing Guidelines for Learning Odyssey

## General Testing Principles

- **Handling Dynamic Narrative Content:**
  - **DO NOT assert against specific LLM-generated narrative text (sentences, paragraphs, character names, etc.).** This content is variable and will break tests.
  - **Focus tests on:**
    - Correct state transitions (`AdventureState` updates).
    - Structural correctness of data (e.g., does a chapter have content? Does a summary have a title?).
    - Presence and type correctness of expected data fields.
    - Correct function calls and interactions between services.
    - Validation of chapter types (`ChapterType`) and sequence.
  - Use mocking to provide structurally correct, but not specific, narrative content when testing components that consume it.

## State Testing

### Summary Button Testing
Run `test_summary_button_flow.py` to verify the "Take a Trip Down Memory Lane" button functionality:
```bash
# Run with default settings (uses realistic state generation)
python tests/test_summary_button_flow.py

# Run with synthetic hardcoded state
python tests/test_summary_button_flow.py --synthetic

# Load state from a file
python tests/test_summary_button_flow.py --file path/to/state.json

# Use specific story category and lesson topic
python tests/test_summary_button_flow.py --category "enchanted_forest_tales" --topic "Singapore History"

# Compare synthetic and realistic states
python tests/test_summary_button_flow.py --compare
```

This test verifies:
1. State storage in StateStorageService
2. State retrieval from StateStorageService
3. State reconstruction with case sensitivity handling
4. Summary data formatting
5. Chapter summaries, educational questions, and statistics

### Chapter Summary Fix Testing
Run `test_chapter_summary_fix.py` to verify the chapter summary inconsistencies fix:
```bash
python tests/test_chapter_summary_fix.py
```

This test verifies:
1. Missing chapter summaries are generated during state storage
2. The CONCLUSION chapter summary is properly generated with a placeholder choice
3. All chapter summaries are stored in the state
4. Chapter titles are properly generated and stored

### Case Sensitivity Testing
Run `test_state_storage_reconstruction.py` to verify case sensitivity handling:
```bash
python tests/test_state_storage_reconstruction.py
```

This test verifies:
1. Uppercase chapter types are correctly converted to lowercase
2. Planned chapter types are correctly converted to lowercase
3. Chapter 10 is correctly treated as a CONCLUSION chapter
4. Summary data is correctly formatted with lowercase chapter types

## Story Simulation Testing

### Full Adventure Simulation
Run `generate_all_chapters.py` to simulate a complete adventure:
```bash
# Run with default settings
python tests/simulations/generate_all_chapters.py

# Specify category and topic
python tests/simulations/generate_all_chapters.py --category "enchanted_forest_tales" --topic "Singapore History"

# Save to specific output file
python tests/simulations/generate_all_chapters.py --output "tests/data/test_adventure.json"
```

This simulation:
1. Generates a complete 10-chapter adventure (9 interactive + 1 conclusion)
2. Creates chapter summaries for each chapter
3. Captures all WebSocket messages and responses
4. Records the complete AdventureState
5. Saves the simulation state to a JSON file

### Chapter Summary Generation
Run `generate_chapter_summaries.py` to generate summaries from a simulation state:
```bash
# Generate chapter summaries
python tests/simulations/generate_chapter_summaries.py --state-file "tests/data/test_adventure.json"

# Generate React-compatible JSON
python tests/simulations/generate_chapter_summaries.py --react-json --state-file "tests/data/test_adventure.json"

# Add delay between API calls
python tests/simulations/generate_chapter_summaries.py --delay 2
```

This script:
1. Extracts chapter content from a simulation state
2. Generates summaries using the LLM
3. Extracts educational questions and statistics
4. Formats data for React or for testing

## Chapter Management Testing

### Chapter Sequence Validation
Run `test_chapter_sequence_validation.py` to verify chapter sequencing:
```bash
python tests/simulations/test_chapter_sequence_validation.py
```

This test verifies:
1. First chapter is STORY type
2. Second-to-last chapter is STORY type
3. Last chapter is CONCLUSION type
4. 50% of remaining chapters are LESSON type
5. No consecutive LESSON chapters
6. REFLECT chapters follow LESSON chapters
7. STORY chapters follow REFLECT chapters

### Chapter Type Assignment
Run `test_chapter_type_assignment.py` to verify chapter type assignment:
```bash
python tests/simulations/test_chapter_type_assignment.py
```

This test verifies:
1. Chapter types are assigned according to the rules
2. The correct ratio of LESSON/REFLECT/STORY chapters is maintained
3. Chapter sequence constraints are enforced

## Data Testing

### Story Loader Testing
Run `test_story_loader.py` to verify story loading:
```bash
python tests/data/test_story_loader.py
```

This test verifies:
1. Story files are loaded correctly
2. Required elements are present
3. File encoding is handled properly

### Lesson Loader Testing
Run `test_lesson_loader.py` to verify lesson loading:
```bash
python tests/data/test_lesson_loader.py
```

This test verifies:
1. Lesson files are loaded correctly
2. Question format is valid
3. Sufficient questions are available

## Frontend Testing Guidelines

### Carousel Component Testing
Test `carousel-manager.js` functionality manually:
* Test with keyboard navigation (arrow keys and Enter)
* Test with touch gestures (swipe left/right)
* Test with button clicks (navigation arrows)
* Test selection functionality
* Verify persistent selection

### Font Size Manager Testing
Test `font-size-manager.js` functionality manually:
* Test size adjustment controls
* Verify persistence across page reloads
* Test show/hide behavior on scroll
* Verify accessibility on different devices

## Critical Debugging Guidelines

### WebSocket Connection Debugging
When debugging WebSocket issues:
1. Check connection establishment in browser console
2. Verify correct URL format (`/ws/story/{story_category}/{lesson_topic}`)
3. Check message handling in `websocket_router.py`
4. Check disconnection handling and reconnection logic
5. Use WebSocket.onclose and WebSocket.onerror handlers for diagnostics

### Subprocess Execution
1. Always use `sys.executable` instead of "python" when creating subprocess commands:
   ```python
   # Correct way to create a subprocess
   cmd = [sys.executable, "path/to/script.py"]
   
   # Incorrect way (may use wrong Python interpreter)
   cmd = ["python", "path/to/script.py"]
   ```
2. This ensures the subprocess uses the same Python interpreter as the main script, with access to all installed packages in the virtual environment.

### State Validation
1. Check question history in `AdventureState`
2. Verify answer selections in `AdventureState`
3. Validate chapter types in `AdventureState`
4. Confirm state transitions in `adventure_state_manager.py`
5. Verify agency tracking in `state.metadata["agency"]`

### Image Generation Debugging
1. Verify API Configuration:
   - Check `GOOGLE_API_KEY` environment variable
   - Confirm API initialization in `image_generation_service.py`
2. Check Request Flow:
   - Trace prompt construction
   - Verify API call parameters
   - Check response handling
3. Analyze Error Handling:
   - Verify retry mechanism (5 retries with exponential backoff)
   - Check null response handling
   - Confirm fallback behavior
4. Agency Choice Visual Details:
   - Verify agency name extraction from choice texts
   - Check visual details extraction
   - Confirm category-specific prefixes

## Key Error Handling Strategies

### Question Errors
- Handle sampling failures in `chapter_manager.py`
- Manage shuffle errors in `chapter_manager.py`
- Track invalid answers in `websocket_service.py`
- Handle missing questions in `chapter_manager.py`

### State Errors
- Handle synchronization failures in `adventure_state_manager.py`
- Implement recovery mechanisms in `adventure_state_manager.py`
- Maintain error boundaries in `adventure_state_manager.py`
- Log state transitions in `adventure_state_manager.py`

### WebSocket Errors
- Handle connection drops in `websocket_router.py`
- Manage reconnection attempts in client-side code
- Process choice errors in `websocket_service.py`
- Handle streaming issues in `websocket_service.py`

### Image Generation Errors
- Handle API failures in `image_generation_service.py`
- Implement retry mechanism with exponential backoff
- Add robust null checking for responses
- Provide graceful degradation when images fail
