# Testing Guidelines for Learning Odyssey

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

## Testing Requirements

### Backend Testing
Run story simulation on changes to:
   - `app/services/llm/*`
   - `app/routers/websocket_router.py`
   - `app/services/websocket_service.py`
   - `app/services/chapter_manager.py`
   - `app/services/image_generation_service.py`
   - `app/models/story.py`
   - `app/init_data.py`
   - `app/data/stories/*.yaml`
   - `app/data/lessons/*.csv`
   - `app/templates/index.html`

### Frontend Testing
Test frontend components manually:
   - `app/static/js/carousel-manager.js`:
     * Test with keyboard navigation (arrow keys and Enter)
     * Test with touch gestures (swipe left/right)
     * Test with button clicks (navigation arrows)
     * Test selection functionality
   - `app/static/js/font-size-manager.js`:
     * Test size adjustment controls
     * Verify persistence across page reloads
     * Test show/hide behavior on scroll

## Critical Debugging Guidelines

### Subprocess Execution
1. Always use `sys.executable` instead of "python" when creating subprocess commands:
   ```python
   # Correct way to create a subprocess
   cmd = [sys.executable, "path/to/script.py"]
   
   # Incorrect way (may use wrong Python interpreter)
   cmd = ["python", "path/to/script.py"]
   ```
2. This ensures the subprocess uses the same Python interpreter as the main script, with access to all installed packages in the virtual environment.

### Question Flow
1. Verify topic selection in `websocket_router.py`.
2. Check sampling logic in `chapter_manager.py`.
3. Confirm shuffle implementation in `chapter_manager.py`.
4. Validate answer tracking in `websocket_service.py`.
5. Verify question persistence in `adventure_state_manager.py`.

### State Validation
1. Check question history in `AdventureState`.
2. Verify answer selections in `AdventureState`.
3. Validate chapter types in `AdventureState`.
4. Confirm state transitions in `adventure_state_manager.py`.
5. Verify agency tracking in `state.metadata["agency"]`.

### Response Chain
1. Verify question format in `websocket_service.py`.
2. Check answer order in `websocket_service.py`.
3. Validate feedback in `websocket_service.py`.
4. Confirm state updates in `adventure_state_manager.py`.
5. Check "chapter" prefix removal in `websocket_service.py`:
   - Verify regex pattern `r"^Chapter(?:\s+\d+)?:?\s*"` catches all variations

### Prompt Debugging
1. Verify State Passing:
   - Check what properties are available in `AdventureState`.
   - Confirm they're being passed to prompt builder in `prompt_engineering.py`.
   - Verify they appear in final prompt.
2. Check Data Flow:
   - Trace data from state to prompt.
   - Look for optional parameters.
   - Verify history inclusion.
3. Verify Adventure Topic Reference:
   - Confirm `state.metadata["non_random_elements"]["name"]` contains the adventure topic name.
   - Check that `_get_phase_guidance()` correctly replaces the {adventure_topic} placeholder in Exposition phase.

### Image Generation Debugging
1. Verify API Configuration:
   - Check `GOOGLE_API_KEY` environment variable.
   - Confirm API initialization in `image_generation_service.py`.
2. Check Request Flow:
   - Trace prompt construction.
   - Verify API call parameters.
   - Check response handling.
3. Analyze Error Handling:
   - Verify retry mechanism (5 retries with exponential backoff).
   - Check null response handling.
   - Confirm fallback behavior.
4. Agency Choice Visual Details:
   - Verify `categories` dictionary is exposed in `prompt_templates.py`.
   - Check agency name extraction from "As a..." choice texts in `enhance_prompt()`.
   - Confirm visual details extraction from square brackets.

## Key Error Handling Strategies

### Question Errors
- Handle sampling failures in `chapter_manager.py`.
- Manage shuffle errors in `chapter_manager.py`.
- Track invalid answers in `websocket_service.py`.
- Handle missing questions in `chapter_manager.py`.

### State Errors
- Handle synchronization failures in `adventure_state_manager.py`.
- Implement recovery mechanisms in `adventure_state_manager.py`.
- Maintain error boundaries in `adventure_state_manager.py`.
- Log state transitions in `adventure_state_manager.py`.

### WebSocket Errors
- Handle connection drops in `websocket_router.py`.
- Manage reconnection attempts in client-side code.
- Process choice errors in `websocket_service.py`.
- Handle streaming issues in `websocket_service.py`.

### Image Generation Errors
- Handle API failures in `image_generation_service.py`.
- Implement retry mechanism with exponential backoff.
- Add robust null checking for responses.
- Provide graceful degradation when images fail.
