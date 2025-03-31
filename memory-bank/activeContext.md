# Active Context

## Current Focus: Chapter Number Calculation Fix in stream_handler.py (2025-03-31)

We've fixed an issue with incorrect chapter number calculation in the `stream_chapter_content` function in `stream_handler.py`. This issue was causing the chapter number to be incorrectly reported as one higher than it should be.

### Problem Analysis

The issue was in how the chapter number was calculated in the `stream_chapter_content` function:

1. **Incorrect Calculation:**
   * The chapter number was calculated as `len(state.chapters) + 1`
   * This calculation assumed the chapter was about to be added to the state
   * However, by the time this function is called, the chapter has already been added to the state

2. **Root Cause:**
   * The function was using a calculation that would be correct before adding a chapter
   * But since the chapter was already added, it was effectively counting the chapter twice

3. **Impact:**
   * Incorrect chapter numbers were being logged (e.g., "Current chapter number calculated as: 4" when processing chapter 3)
   * This could potentially affect image generation and other processes that rely on the correct chapter number

### Implemented Solution

We modified the chapter number calculation in `stream_handler.py`:

1. **Updated Calculation:**
   * Changed from `current_chapter_number = len(state.chapters) + 1` to `current_chapter_number = len(state.chapters)`
   * Updated the comment to clarify that the chapter has already been added to the state at this point

2. **Implementation Details:**
   * The fix was isolated to the `stream_chapter_content` function in `stream_handler.py`
   * Other files (`content_generator.py` and `choice_processor.py`) correctly calculate the chapter number as they are called before the chapter is added to the state

3. **Benefits:**
   * Correct chapter numbers are now reported in logs
   * Image generation and other processes now use the correct chapter number
   * Improved code clarity with better comments explaining the calculation

### Verification

We verified that the other files (`content_generator.py` and `choice_processor.py`) correctly calculate the chapter number as `len(state.chapters) + 1` because they are called before the new chapter is added to the state. Only `stream_handler.py` needed to be fixed.

## Previous Focus: Image Consistency Improvement for CONCLUSION Chapter (2025-03-29)

We've implemented a fix to ensure an image is generated at the end of the last chapter (CONCLUSION chapter) of the adventure. Previously, the CONCLUSION chapter was not displaying an image, creating an inconsistent experience compared to all other chapters.

### Problem Analysis

The issue was due to the different streaming flow used for the CONCLUSION chapter:

1. **Different Streaming Flows:**
   * Regular chapters use `stream_chapter_content` in `stream_handler.py`, which includes image generation
   * The CONCLUSION chapter was using `send_story_complete` in `core.py`, which only streamed text without generating images

2. **Root Cause:**
   * The `send_story_complete` function was not calling the image generation functions
   * It only called `stream_conclusion_content` to stream the text content
   * No image generation was triggered for the CONCLUSION chapter

3. **Impact:**
   * Users did not see an image for the final chapter of their adventure
   * This created an inconsistent experience compared to all other chapters
   * The character's agency choice was not visually represented in the conclusion

### Implemented Solution

We modified the `send_story_complete` function in `app/services/websocket/core.py` to include image generation for the CONCLUSION chapter:

1. **Added Image Generation:**
   * Imported the necessary image generation functions
   * Added code to start image generation tasks before streaming content
   * Added code to process image tasks after sending the completion message

2. **Implementation Details:**
   * Used the same standardized approach for image generation as other chapters
   * Maintained the existing flow of streaming text first, then processing images
   * Added appropriate error handling and logging

3. **Benefits:**
   * Consistent image generation across all chapters, including the CONCLUSION
   * Visual representation of the character's agency choice in the final chapter
   * Enhanced user experience with a complete visual narrative

### Future Considerations

1. **Summary Chapter Images:**
   * Consider whether the SUMMARY chapter should also have images
   * This would require similar modifications to the `handle_reveal_summary` function

2. **Image Generation Timing:**
   * The current implementation starts image generation before streaming content
   * This approach prioritizes getting the image generation started early
   * Alternative approach could be to start image generation after sending the completion message

3. **Fallback Images:**
   * The implementation includes error handling and fallback to an empty image task list
   * Consider adding a specific fallback image for the CONCLUSION chapter if needed

## Previous Focus: Agency Visual Details Enhancement for Image Generation (2025-03-29)

We've implemented a comprehensive solution to improve how agency choices are represented in generated images. The previous implementation had several limitations:

1. **Inconsistent Representation**: The image model had no context about what agency elements (companions, abilities, artifacts, professions) should look like.
2. **Lost Visual Details**: Rich visual descriptions defined in `prompt_templates.py` weren't utilized in image generation prompts.
3. **Undifferentiated Agency Types**: No distinction between different types of agency in how they were described in prompts.
4. **Disconnection from Narrative**: Agency elements often didn't appear integrated into the scene in a way that reflected their role in the story.

### Implemented Solution

We've implemented a comprehensive solution to enhance agency representation in generated images:

1. **Enhanced Agency Storage**:
   * Modified `process_story_response` in `choice_processor.py` to extract and store additional agency information when the first chapter choice is made
   * Extracted visual details from the square brackets in `prompt_templates.py` (e.g., "[a swirling figure with hands sparking flames...]")
   * Stored this information in `state.metadata["agency"]` for use throughout the adventure

2. **Improved Prompt Construction**:
   * Updated `enhance_prompt` in `image_generation_service.py` to use the stored agency details
   * Implemented category-specific prefixes (e.g., "He/she is accompanied by" for companions, "He/she has the power of" for abilities)
   * Included the visual details in parentheses after the agency name
   * Replaced "Fantasy illustration of" with "Colorful storybook illustration of this scene:" for a more child-friendly style
   * Changed the comma before agency descriptions to a period for better readability
   * Removed the story name, visual details, and base style ("vibrant colors, detailed, whimsical, digital art") from the prompt
   * Focused on the chapter summary and agency representation in the prompt

3. **Added Fallback Mechanism**:
   * Implemented a fallback lookup mechanism for cases where visual details might not be stored correctly
   * This ensures backward compatibility with existing adventures

### Results

The image generation prompts are now much more detailed and contextually appropriate. For example:

**Before:**
```
Fantasy illustration of A giant mushroom pulses blue light in a forest clearing, illuminating the forest floor with spiderwebs. Shimmering bees swarm the mushroom as massive webs glow with intricate patterns., featuring Element Bender, in Festival of Lights & Colors, with Rainbow Cascade: A waterfall refracting sunlight into vivid arcs, shimmering more brilliantly after acts of harmony or camaraderie., vibrant colors, detailed, whimsical, digital art
```

**After:**
```
Colorful storybook illustration of this scene: A giant mushroom pulses blue light in a forest clearing, illuminating the forest floor with spiderwebs. Shimmering bees swarm the mushroom as massive webs glow with intricate patterns. He/she has the power of Element Bender (a swirling figure with hands sparking flames, splashing water, tossing earth, and twirling breezes in a dance)
```

This results in more consistent and accurate visual representations of agency elements in the generated images, enhancing the overall storytelling experience.

## Previous Focus: WebSocket, Template Structure, and Paragraph Formatter Improvements (2025-03-25)

We've completed two major refactorings and an important paragraph formatter enhancement to improve code organization, maintainability, modularity, and text formatting quality:

### 1. WebSocket Service Refactoring

We've restructured the WebSocket services by breaking down the monolithic `websocket_service.py` into specialized components:

- **Core Components**:
  * `core.py`: Central coordination of WebSocket operations and message handling
  * `choice_processor.py`: Processing user choices and chapter transitions
  * `content_generator.py`: Generating chapter content based on state
  * `image_generator.py`: Managing image generation for agency choices and chapters
  * `stream_handler.py`: Handling content streaming to clients
  * `summary_generator.py`: Managing summary generation and display

- **Key Improvements**:
  * Enhanced code organization with clear separation of concerns
  * Improved modularity for easier maintenance and future extensions
  * Implemented robust error handling throughout the WebSocket flow
  * Added asynchronous handling of user choices and chapter streaming
  * Enhanced image generation to support agency choices and chapter-specific images
  * Improved logging for easier debugging and monitoring

### 2. Template Structure Refactoring

We've implemented a modular template system to improve frontend organization and maintainability:

- **Template Components**:
  * Created a base layout (`layouts/main_layout.html`)
  * Extracted reusable components:
    - `components/category_carousel.html`
    - `components/lesson_carousel.html`
    - `components/loader.html`
    - `components/scripts.html`
    - `components/stats_display.html`
    - `components/story_container.html`
  * Updated the main index page to use this component structure

- **Key Improvements**:
  * Better organization with clear separation of UI components
  * Enhanced code reusability through component extraction
  * Improved maintainability with smaller, focused template files
  * Clearer structure for future UI enhancements

### 3. Paragraph Formatter Enhancement

We've improved the paragraph formatting implementation in `app/services/llm/paragraph_formatter.py` and `app/services/llm/providers.py` to better handle text that lacks proper paragraph formatting:

- **New Regeneration-First Approach**:
  * When improperly formatted text is detected, the system now first tries regenerating with the original prompt
  * Makes up to 3 regeneration attempts before falling back to specialized reformatting
  * Preserves full story context in regeneration attempts, ensuring narrative continuity
  * Maintains proper chapter references and story elements

- **Implementation Details**:
  * Modified both OpenAI and Gemini implementations to use the same regeneration approach
  * Enhanced logging to track regeneration attempts and success/failure
  * Added robust error handling to ensure the story continues even if regeneration fails
  * Preserved the original fallback mechanism as a last resort

- **Key Benefits**:
  * More natural-sounding text with better formatting
  * Reduced risk of content distortion since we're using the original story prompt
  * Improved content consistency with full context preservation
  * Better debugging capabilities with enhanced logging

These improvements have significantly enhanced both the code structure and content quality while maintaining all existing functionality.

## Previous Focus: Summary Chapter Race Condition Fix (2025-03-23)

We've successfully implemented and verified a solution to fix the race condition in the Summary Chapter feature and addressed a related issue where the WebSocket message was missing the state data. The Summary Chapter is now correctly displaying all data (questions, answers, chapter summaries, and titles).

### Race Condition Solution

The race condition was occurring because there were two separate paths for storing the state and getting a state_id:

1. **REST API Path** (in `viewAdventureSummary()` function):
   * Immediately stores the current state via REST API when the button is clicked
   * Redirects to the summary page with the state_id from the REST API

2. **WebSocket Path** (in WebSocket message handler):
   * Processes the "reveal_summary" choice asynchronously
   * Stores the state after generating the CONCLUSION chapter summary
   * Sends a "summary_ready" message with the state_id to the client

This created a race condition where:
* The REST API path might complete before the WebSocket path has finished generating the CONCLUSION chapter summary
* This can lead to incomplete data being displayed in the Summary Chapter
* Only 9 chapter summaries might be displayed instead of all 10

### Implementation Details

We've modified the `viewAdventureSummary()` function in `app/templates/index.html` to use the WebSocket flow exclusively, with a fallback to the REST API for robustness:

1. **Primary WebSocket Flow**:
   * Sends the "reveal_summary" message via WebSocket
   * Sets a 5-second timeout for the WebSocket response
   * Overrides the onmessage handler to catch the "summary_ready" message
   * Uses the state_id from the WebSocket response to navigate to the summary page

2. **Fallback REST API Flow**:
   * Activates if WebSocket is not available or times out
   * Uses the existing REST API approach as a fallback
   * Ensures we don't have duplicate redirects

3. **Additional Improvements**:
   * Added a flag to track if we've already redirected
   * Added detailed logging for debugging
   * Improved error handling

### Testing

The race condition fix has been thoroughly tested and verified. The solution was initially tested with a dedicated test HTML file that simulated various timing scenarios, and after verification, the test file has been removed as it's no longer needed:

1. **WebSocket Success**: WebSocket responds quickly with state_id
2. **WebSocket Timeout**: WebSocket doesn't respond within timeout period, fallback to REST API
3. **WebSocket Not Available**: WebSocket is not available, immediate fallback to REST API

### Benefits

This solution:
* Eliminates the race condition by primarily using the WebSocket flow
* Ensures the state stored always includes the CONCLUSION chapter summary
* Reduces duplicate processing
* Creates a clearer, more linear flow from button click to summary display
* Maintains compatibility with the REST API flow as a fallback
* Improves user experience by ensuring complete data is displayed in the Summary Chapter

## Previous Focus: Missing State Storage Fix (2025-03-23)

We've implemented a solution to fix the Summary Chapter issues described in `docs/missing_state_storage.md`. The issues were related to duplicate summary generation and placeholder content display when using the "Take a Trip Down Memory Lane" button.

### Problem Analysis

The root cause of these issues was a missing integration step between the WebSocket flow (during the adventure) and the REST API flow (when viewing the summary):

1. **Missing State Storage**: After generating the CONCLUSION chapter summary in the WebSocket flow, there was no explicit call to store the updated state in the `StateStorageService`.

2. **Duplicate Summary Generation**: When the React app loaded the summary page, it retrieved an incomplete state and regenerated summaries unnecessarily.

### Implementation Details

1. **Added Explicit State Storage in WebSocket Flow**:
   * Modified `app/services/websocket_service.py` to store the updated state in `StateStorageService` after generating the CONCLUSION chapter summary
   * Added code to send the state_id to the client in a new "summary_ready" message type
   ```python
   # Store the updated state in StateStorageService
   from app.services.state_storage_service import StateStorageService
   state_storage_service = StateStorageService()
   state_id = await state_storage_service.store_state(state.dict())
   
   # Include the state_id in the response to the client
   await websocket.send_json({
       "type": "summary_ready",
       "state_id": state_id
   })
   ```

2. **Updated Client-Side Code**:
   * Modified `app/templates/index.html` to handle the new "summary_ready" message type
   * Added code to navigate directly to the summary page with the state_id from the WebSocket response
   ```javascript
   else if (data.type === 'summary_ready') {
       // Use the state_id from the WebSocket response
       const stateId = data.state_id;
       
       // Navigate to the summary page with this state_id
       window.location.href = `/adventure/summary?state_id=${stateId}`;
   }
   ```

3. **Fixed Duplicate Summary Generation**:
   * Updated `app/services/summary/service.py` to only generate summaries if they're actually missing
   * Added condition to check if existing summaries are complete before regenerating them
   ```python
   # Only generate summaries if they're actually missing
   if state_data.get("chapters") and (
       not state_data.get("chapter_summaries") or 
       len(state_data.get("chapter_summaries", [])) < len(state_data.get("chapters", []))
   ):
       logger.info("Missing chapter summaries detected, generating them now")
       await self.chapter_processor.process_stored_chapter_summaries(state_data)
   else:
       logger.info("All chapter summaries already exist, skipping generation")
   ```

4. **Improved Logging and Error Handling**:
   * Added detailed logging in `app/services/state_storage_service.py` to track state storage and retrieval
   * Added logging about chapter counts and summary counts to help with debugging
   ```python
   # Add more detailed logging about the state content
   logger.info(
       f"Storing state with {len(state_data.get('chapters', []))} chapters and {len(state_data.get('chapter_summaries', []))} summaries"
   )
   
   # Add more detailed logging about the retrieved state content
   retrieved_state = state_data["state"]
   logger.info(
       f"Retrieved state with {len(retrieved_state.get('chapters', []))} chapters and {len(retrieved_state.get('chapter_summaries', []))} summaries"
   )
   ```

### Benefits

1. **Eliminated Duplicate Summary Generation**:
   * The system now checks if summaries already exist before regenerating them
   * This avoids unnecessary processing and potential inconsistencies

2. **Fixed Placeholder Content Display**:
   * The Summary Chapter now shows the actual content generated during the adventure
   * The state with complete summaries is properly stored and retrieved

3. **Improved Debugging Capabilities**:
   * Enhanced logging makes it easier to track state storage and retrieval
   * Detailed information about chapter counts and summary counts helps with troubleshooting

4. **Streamlined User Experience**:
   * The user is now automatically redirected to the summary page with the correct state_id
   * No more need to manually store the state and generate a new state_id

### Testing

The solution has been tested with the following scenarios:
* Clicking the "Take a Trip Down Memory Lane" button after completing an adventure
* Verifying that summaries are not regenerated when viewing the summary page
* Confirming that actual content is displayed instead of placeholders
* Testing edge cases like missing summaries or invalid state_id
