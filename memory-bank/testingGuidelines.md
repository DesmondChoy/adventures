# Testing Guidelines for Learning Odyssey

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
   - `app/data/lessons.csv`
   - `app/templates/index.html`

### Frontend Testing
Test frontend components manually:
   - `app/static/js/carousel-manager.js`:
     * Test with keyboard navigation (arrow keys and Enter)
     * Test with touch gestures (swipe left/right)
     * Test with button clicks (navigation arrows)
     * Test selection functionality
     * Verify mobile-specific optimizations
   - `app/static/js/font-size-manager.js`:
     * Test size adjustment controls
     * Verify persistence across page reloads
     * Test show/hide behavior on scroll
     * Verify mobile-only display

## Debugging Guidelines

### Subprocess Execution
1. Always use `sys.executable` instead of "python" when creating subprocess commands:
   ```python
   # Correct way to create a subprocess
   cmd = [sys.executable, "path/to/script.py"]
   
   # Incorrect way (may use wrong Python interpreter)
   cmd = ["python", "path/to/script.py"]
   ```
2. This ensures the subprocess uses the same Python interpreter as the main script, with access to all installed packages in the virtual environment.
3. This is particularly important for:
   - `run_simulation_tests.py` when running `story_simulation.py`
   - Any script that needs to execute Python code in a subprocess
   - Testing frameworks that spawn multiple processes

### Question Flow
1. Verify topic selection in `websocket_router.py`.
2. Check sampling logic in `chapter_manager.py`.
3. Confirm shuffle implementation in `chapter_manager.py`.
4. Validate answer tracking in `websocket_service.py`.
5. Verify question persistence in `adventure_state_manager.py`.
6. Test response creation in `websocket_service.py`.
7. Check state consistency in `adventure_state_manager.py`.
8. Monitor error handling.

### State Validation
1. Check question history in `AdventureState`.
2. Verify answer selections in `AdventureState`.
3. Validate chapter types in `AdventureState`.
4. Confirm state transitions in `adventure_state_manager.py`.
5. Test question persistence in `adventure_state_manager.py`.
6. Verify response handling in `websocket_service.py`.
7. Check error recovery in `adventure_state_manager.py`.
8. Monitor state consistency.
9. Verify agency tracking in `state.metadata["agency"]`.

### Response Chain
1. Verify question format in `websocket_service.py`.
2. Check answer order in `websocket_service.py`.
3. Validate feedback in `websocket_service.py`.
4. Confirm state updates in `adventure_state_manager.py`.
5. Test question handling in `websocket_service.py`.
6. Verify response creation in `websocket_service.py`.
7. Check "chapter" prefix removal in `websocket_service.py`:
   - Verify regex pattern `r"^Chapter(?:\s+\d+)?:?\s*"` catches all variations
   - Confirm removal in `process_choice()`, `stream_and_send_chapter()`, and `generate_chapter()`
   - Check capitalization of first letter after removal
8. Check error handling.
9. Monitor state consistency.
10. Verify agency evolution in REFLECT chapters.

### Prompt Debugging
1. Verify State Passing:
   - Check what properties are available in `AdventureState`.
   - Confirm they're being passed to prompt builder in `prompt_engineering.py`.
   - Verify they appear in final prompt.
2. Check Data Flow:
   - Trace data from state to prompt.
   - Look for optional parameters.
   - Verify history inclusion.
3. Analyze Prompt Content:
   - Review complete prompt output.
   - Check for missing context.
   - Verify continuity elements.
   - Confirm agency references.
4. Verify Adventure Topic Reference:
   - Confirm `state.metadata["non_random_elements"]["name"]` contains the adventure topic name.
   - Check that `_get_phase_guidance()` correctly replaces the {adventure_topic} placeholder in Exposition phase.
   - Verify the final prompt includes the specific adventure topic name in the world building section.

### Frontend Component Debugging
1. Carousel Component:
   - Verify initialization parameters:
     * Check that `elementId` points to a valid DOM element
     * Confirm `itemCount` matches the actual number of carousel cards
     * Verify `dataAttribute` is correctly set for selection
     * Check that `inputId` points to a valid input element
     * Confirm `onSelect` callback is properly defined
   - Test rotation functionality:
     * Verify rotation angle calculation (`360 / itemCount`)
     * Check that cards are positioned correctly in 3D space
     * Confirm active card is updated after rotation
   - Test selection functionality:
     * Verify selected card gets proper CSS classes
     * Check that input element is updated with selected value
     * Confirm onSelect callback is called with correct value
   - Test event handling:
     * Verify keyboard navigation works (arrow keys and Enter)
     * Check touch event handling (swipe gestures)
     * Confirm click handlers on cards work properly
   - Mobile-specific testing:
     * Verify swipe tip is hidden after first touch
     * Check that active card scaling works correctly on mobile
     * Confirm touch events prevent default scrolling behavior

2. Font Size Manager:
   - Verify initialization:
     * Check that it only initializes on mobile devices (screen width ≤ 768px)
     * Confirm default font size is set to 100%
     * Verify localStorage persistence works
   - Test size adjustment:
     * Check that increase/decrease buttons work correctly
     * Verify min/max limits (80% to 200%)
     * Confirm percentage display updates correctly
     * Check that content size actually changes
   - Test show/hide behavior:
     * Verify controls show on page load
     * Check that controls hide on scroll down
     * Confirm controls show again on scroll up
     * Verify transitions are smooth

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
   - Verify multi-stage matching approach in `websocket_service.py`:
     * Direct match with extracted agency name
     * Match with full choice text
     * Fallback to agency_lookup if direct category access fails
   - Check final prompt format includes visual details in square brackets.
5. Gender Consistency:
   - Verify choice text is passed to `enhance_prompt()`.
   - Check that narrative text with gender indicators is incorporated in image prompts.
   - Confirm generated images maintain gender consistency with narrative.

## Error Handling

### Question Errors
- Handle sampling failures in `chapter_manager.py`.
- Manage shuffle errors in `chapter_manager.py`.
- Track invalid answers in `websocket_service.py`.
- Log question issues in `chapter_manager.py`.
- Handle missing questions in `chapter_manager.py`.
- Recover from errors in `chapter_manager.py`.
- Maintain state consistency in `adventure_state_manager.py`.
- Log error details.

### State Errors
- Handle synchronization failures in `adventure_state_manager.py`.
- Implement recovery mechanisms in `adventure_state_manager.py`.
- Maintain error boundaries in `adventure_state_manager.py`.
- Log state transitions in `adventure_state_manager.py`.
- Handle question errors in `adventure_state_manager.py`.
- Recover from failures in `adventure_state_manager.py`.
- Ensure data consistency in `adventure_state_manager.py`.
- Monitor error patterns.

### WebSocket Errors
#### Router-Level Errors (`websocket_router.py`)
- Handle connection drops.
- Manage reconnection attempts.
- Log connection lifecycle events.
- Validate incoming messages.
- Coordinate error recovery with service.
- Monitor connection health.
- Handle client disconnects gracefully.
- Maintain connection state.

#### Service-Level Errors (`websocket_service.py`)
- Handle content generation failures.
- Manage state transitions.
- Process choice errors.
- Handle streaming issues.
- Validate message formats.
- Provide fallback responses.
- Maintain data consistency.
- Monitor processing health.

### Image Generation Errors
- Handle API failures in `image_generation_service.py`.
- Implement retry mechanism with exponential backoff.
- Add robust null checking for responses.
- Provide graceful degradation when images fail.
- Log detailed error information.
- Maintain text streaming performance.

### Frontend Component Errors
#### Carousel Component Errors
- Handle missing DOM elements gracefully in constructor.
- Provide fallback for invalid itemCount values.
- Check for undefined dataAttribute values.
- Validate inputId exists before updating.
- Handle touch event errors on mobile devices.
- Provide console warnings for initialization issues.
- Implement error boundaries for event handlers.
- Ensure proper cleanup of event listeners.

#### Font Size Manager Errors
- Handle localStorage access errors.
- Provide fallbacks for invalid size values.
- Validate DOM elements exist before manipulation.
- Handle scroll event errors gracefully.
- Ensure proper initialization on different devices.
- Implement error recovery for failed size adjustments.
