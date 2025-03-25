# Active Context

## Current Focus: WebSocket, Template Structure, and Paragraph Formatter Improvements (2025-03-25)

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

We've also created a test HTML file (`test_summary_button.html`) that simulates both the WebSocket and REST API paths with various timing scenarios to ensure the race condition is eliminated:

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

## Previous Focus: Summary Router Refactoring (2025-03-23)

We've completed a major refactoring of the summary_router.py file, converting it from a single monolithic file into a properly organized modular package. This improves code maintainability, testability, and extensibility while preserving all existing functionality.

### Implementation Details

1. **Created Modular Package Structure**:
   * Converted the single large file into a properly organized package in `app/services/summary/`
   * Created clear component separation with specialized files for each responsibility
   * Implemented proper package exports through `__init__.py`
   * Added comprehensive unit tests in `tests/test_summary_service.py`

2. **Separated Components by Responsibility**:
   * `exceptions.py`: Custom exception classes (SummaryError, StateNotFoundError, SummaryGenerationError)
   * `helpers.py`: Utility functions and helper classes (ChapterTypeHelper)
   * `dto.py`: Data transfer objects (AdventureSummaryDTO)
   * `chapter_processor.py`: Chapter-related processing logic
   * `question_processor.py`: Question extraction and processing
   * `stats_processor.py`: Statistics calculation
   * `service.py`: Main service class that orchestrates the components

3. **Reduced Method Sizes**:
   * Split large methods into focused, smaller methods with single responsibilities
   * Improved readability with better method naming and organization
   * Enhanced error handling with specific exception types
   * Added comprehensive logging throughout the codebase

4. **Simplified Main Service**:
   * Created `SummaryService` class that delegates to specialized component classes
   * Implemented clear separation of concerns
   * Made the code more testable with dependency injection
   * Improved error handling and recovery mechanisms

### Benefits

1. **Improved Maintainability**:
   * Smaller, focused files are easier to understand and modify
   * Clear separation of concerns makes the code more predictable
   * Better organization reduces cognitive load when working with the codebase
   * Comprehensive logging helps with debugging and troubleshooting

2. **Enhanced Testability**:
   * Isolated components can be tested independently
   * Dependency injection makes unit testing simpler
   * Specialized mock objects can be used for testing specific components
   * Comprehensive test coverage ensures reliability

3. **Better Extensibility**:
   * Adding new features is easier with the modular structure
   * Components can be enhanced independently
   * Clear interfaces between components reduce coupling
   * New functionality can be added with minimal changes to existing code

## Previous Focus: Chapter Summary Inconsistencies Fix (2025-03-23)

We've implemented a solution to address inconsistencies in chapter summaries between the WebSocket flow and the REST API flow when a user clicks the "Take a Trip Down Memory Lane" button. This ensures that all chapter summaries, including the CONCLUSION chapter summary, are properly generated and stored.

### Implementation Details

1. **Enhanced State Storage Process**:
   * Modified `store_adventure_state` function in `app/routers/summary_router.py` to check for missing chapter summaries
   * Added logic to generate summaries for chapters that don't have them, including the CONCLUSION chapter
   * Implemented special handling for the CONCLUSION chapter with a placeholder choice ("End of story")
   * Added robust error handling and fallback mechanisms for edge cases

2. **Comprehensive Testing**:
   * Created `tests/test_chapter_summary_fix.py` to verify the solution
   * Test confirms that summaries are generated for all chapters, including the CONCLUSION chapter
   * Verified that the state is properly stored with complete chapter summaries

3. **Benefits**:
   * Ensures consistent chapter summaries in the Summary Chapter
   * Eliminates duplicate summary generation
   * Works with the existing frontend code (no client-side changes needed)
   * Handles edge cases gracefully with fallback mechanisms

## Previous Focus: Backend-Frontend Naming Consistency (2025-03-23)

We've implemented a centralized solution for handling naming inconsistencies between the backend (Python/snake_case) and frontend (JavaScript/camelCase). This improves code maintainability and reduces potential errors.

### Implementation Details

1. **Centralized Conversion Utility**:
   * Created `app/utils/case_conversion.py` with utility functions for case conversion
   * Implemented `to_camel_case()` and `snake_to_camel_dict()` for converting snake_case to camelCase
   * Added `to_snake_case()` and `camel_to_snake_dict()` for potential future use (converting camelCase to snake_case)
   * The utility handles nested dictionaries and lists recursively

2. **Standardized Backend Code**:
   * Modified backend functions to consistently use snake_case
   * Updated field names to be more semantically consistent (e.g., `user_answer` instead of `chosen_answer`)
   * Ensured all data structures in the backend follow Python conventions

3. **API Boundary Conversion**:
   * Applied conversion at the API endpoint level in `get_adventure_summary()`
   * Backend code uses snake_case internally
   * Frontend receives camelCase data
   * This approach respects the conventions of each language

### Benefits

1. **Improved Maintainability**:
   * Centralized conversion logic reduces duplication
   * Easier to add new fields or modify existing ones
   * Clearer separation between data extraction/formatting and API response formatting

2. **Reduced Potential for Errors**:
   * Consistent naming conventions throughout the backend code
   * Automated conversion reduces manual errors
   * Better type safety and predictability

3. **Better Developer Experience**:
   * Backend developers can work with Python conventions
   * Frontend developers receive data in JavaScript conventions
   * Clearer code organization and responsibility boundaries

## Previous Focus: STORY_COMPLETE Event Implementation (2025-03-23)

We've implemented changes to the STORY_COMPLETE event to make it more consistent and maintainable. The STORY_COMPLETE event is a critical part of the adventure flow that marks the completion of the interactive story chapters and prepares for the CONCLUSION chapter.

### Implementation Changes

We made two key changes to the STORY_COMPLETE event implementation:

1. **Simplified Event Trigger Condition**:
   * Changed the event trigger to only check if the chapter count equals the story length
   * Removed the additional check for the last chapter being a CONCLUSION type
   * This makes the code more flexible for future changes to story length

2. **Consistent Summary Generation**:
   * Updated the "Take a Trip Down Memory Lane" button handling to create a placeholder response for the CONCLUSION chapter
   * For regular chapters, summaries are generated when a user makes a choice, which creates a chapter response
   * The CONCLUSION chapter doesn't have choices, but we now treat the "Take a Trip Down Memory Lane" button as a choice (with "reveal_summary" as the chosen_path)
   * When the button is clicked, we create a placeholder response for the CONCLUSION chapter (chosen_path="end_of_story", choice_text="End of story")
   * This allows the CONCLUSION chapter to go through the same summary generation process as other chapters
   * The consistent approach simplifies the code and makes it more maintainable

### Benefits of the Changes

1. **Consistency in Code Logic**:
   * All chapters, including the CONCLUSION chapter, now go through the same summary generation process
   * The code is more consistent and easier to understand
   * Future changes to the summary generation process only need to be made in one place

2. **Flexibility for Future Changes**:
   * The code will work correctly if story length changes in the future
   * We rely on the existing validation in `determine_chapter_types()` to ensure the last chapter is a CONCLUSION type
   * The implementation is more adaptable to future requirements

3. **Improved Maintainability**:
   * Reduced special case handling makes the code more maintainable
   * Reusing existing code paths rather than duplicating logic
   * Making the behavior more predictable and easier to reason about

## Previous Focus: Enhanced Summary Chapter Robustness (2025-03-23)

We've updated our documentation to reflect that the application now includes a Summary Chapter that follows the Conclusion Chapter. The Summary Chapter doesn't contain any narrative content but instead shows statistics and a chapter-by-chapter summary of earlier chapters.

We've further improved the "Trip down memory lane" button functionality by enhancing the robustness of the summary chapter. The button now works correctly in all scenarios, even when chapter summaries and educational questions are not properly captured or stored.

### Solution Summary

The issue was related to three main problems:

1. **Missing Chapter Summaries and Educational Questions:**
   * When the state was stored and retrieved, chapter summaries and educational questions were sometimes missing
   * We enhanced the `format_adventure_summary_data()` method in `adventure_state_manager.py` to generate placeholder summaries when none are found
   * We improved title extraction with fallback to generic titles
   * We added better handling for missing educational questions, including a fallback question
   * We ensured statistics are always valid, even when no questions are found

2. **Case Sensitivity in Chapter Types:**
   * The stored state contained uppercase chapter types (like "STORY", "LESSON", "CONCLUSION"), but the AdventureState model expected lowercase values (like "story", "lesson", "conclusion")
   * While there was code to handle this case conversion, it wasn't properly updating the chapter type to CONCLUSION
   * We enhanced the case sensitivity handling to not just detect uppercase chapter types but actually convert them to lowercase
   * We added special handling for the last chapter to ensure it's always treated as a CONCLUSION chapter, regardless of the total story length

3. **Duplicate state_id Parameter Issue:**
   * The URL for the summary page sometimes contained duplicate state_id parameters, which caused issues with how the state was retrieved
   * We added code in `summary_router.py` to detect and handle duplicate state_id parameters
   * We updated `summary-state-handler.js` to clean up state_id values that might contain duplicates
   * We enhanced `react-app-patch.js` to properly handle URLs with existing state_id parameters

### Recent Improvements

We've made the summary chapter more robust by:

1. **Enhanced Question Extraction in `generate_chapter_summaries.py`:**
   * Added case-insensitive chapter type matching to properly identify LESSON chapters
   * Improved handling of questions without chapter matches to ensure they're still included
   * Added fallback questions when no questions are found to ensure the summary page always has content
   * Enhanced error handling to prevent failures when question data is incomplete

2. **Improved Statistics Calculation in `generate_chapter_summaries.py`:**
   * Now uses actual chapter counts instead of relying solely on story_length
   * Added robust error handling with fallback values when question extraction fails
   * Ensured statistics are always valid (no more correct answers than questions, at least one question)
   * Added better logging to track statistics calculation

3. **Enhanced Summary Data Formatting in `adventure_state_manager.py`:**
   * Added generation of placeholder summaries when none are found
   * Improved title extraction with fallback to generic titles
   * Added better handling for missing educational questions
   * Ensured statistics are always valid, even when no questions are found
   * Added fallback question when LESSON chapters exist but no questions are extracted

### Recent Improvements

We've made the code more flexible by removing hardcoded references to Chapter 10:

1. **Focus on Last Chapter Instead of Chapter 10:**
   * Previously, the code had hardcoded checks for Chapter 10 being the CONCLUSION chapter
   * We've updated the code to focus on the last chapter (at position `story_length`) being the CONCLUSION chapter
   * This makes the code more future-proof, as it will work even if the story length changes
   * Changes were made in both `adventure_state_manager.py` and `summary_router.py`

2. **More Robust CONCLUSION Chapter Detection:**
   * We've improved the logic for detecting and handling the CONCLUSION chapter
   * The code now properly identifies the last chapter as the CONCLUSION chapter
   * It also updates the chapter type to CONCLUSION if needed
   * This ensures the "Trip down memory lane" button works correctly regardless of the adventure's length

## Previous Focus: Case Sensitivity in Chapter Types (2025-03-22)

We initially identified that the "Take a Trip Down Memory Lane" button issue was related to case sensitivity in chapter types. The problem was that the stored state contained uppercase chapter types (like "STORY", "LESSON"), but the AdventureState model expected lowercase values (like "story", "lesson").

### Problem Description

1. **Initial 404 Error:**
   * When clicking the "Take a Trip Down Memory Lane" button, users were getting a 404 Not Found error
   * The error occurred when trying to access `/adventure/summary?state_id=<UUID>`
   * The state was being stored successfully, but the summary page wasn't being served

2. **Routing Issue Fix:**
   * We fixed the routing issue by moving the catch-all route in summary_router.py to the end of the file
   * This ensured that specific routes like `/summary` were processed before the catch-all route
   * The summary page now loads, but we were encountering validation errors

3. **Validation Errors:**
   * When retrieving the stored state, we were getting validation errors from the AdventureState model:
   ```
   Error parsing stored state: 3 validation errors for AdventureState
   selected_theme
     Value error, Field cannot be empty [type=value_error, input_value='', input_type=str]
   selected_moral_teaching
     Value error, Field cannot be empty [type=value_error, input_value='', input_type=str]
   selected_plot_twist
     Value error, Field cannot be empty [type=value_error, input_value='', input_type=str]
   ```
   * These fields are required by the AdventureState model and cannot be empty strings

4. **Case Sensitivity Issue:**
   * After fixing the validation errors, we encountered a new issue with case sensitivity in chapter types
   * The error message showed:
   ```
   Error serving summary data: 500: Error reconstructing state: 500: Failed to reconstruct adventure state
   ```
   * The stored state contained uppercase chapter types (like "STORY", "LESSON"), but the AdventureState model expected lowercase values (like "story", "lesson")

### Root Cause Analysis

After extensive debugging, we identified two main issues:

1. **StateStorageService Implementation Issue:**
   * The `StateStorageService` was using a non-singleton pattern with a simple in-memory cache (`self.memory_cache = {}`)
   * Each instance of `StateStorageService` had its own separate memory cache
   * This meant that the state stored by one instance couldn't be found by another instance
   * When the state was stored during the adventure (by one instance), it was saved in that instance's memory cache
   * When the summary page tried to retrieve the state (using a different instance), it was looking in a completely different memory cache

2. **Case Sensitivity in Chapter Types:**
   * The `AdventureState` model's `ChapterType` enum defines lowercase values:
   ```python
   class ChapterType(str, Enum):
       LESSON = "lesson"
       STORY = "story"
       CONCLUSION = "conclusion"
       REFLECT = "reflect"
       SUMMARY = "summary"
   ```
   * But the stored state was using uppercase values like "STORY" and "LESSON"
   * This caused validation errors when creating the AdventureState object

### Solutions Implemented

1. **Implemented Singleton Pattern for StateStorageService:**
   * Modified `StateStorageService` to use a singleton pattern with a shared memory cache
   * Added class variables `_instance`, `_memory_cache`, and `_initialized` to ensure all instances share the same memory cache
   * Implemented `__new__` method to return the same instance for all calls
   * Updated methods to use the class variable `_memory_cache` instead of instance variable
   * Added detailed logging to track state storage and retrieval
   * Modified `main.py` to explicitly set the singleton instance

2. **Added Case Sensitivity Handling:**
   * Modified the `reconstruct_state_from_storage` method in `AdventureStateManager` to convert all chapter types to lowercase
   * Added code to convert each chapter's `chapter_type` to lowercase
   * Updated the story chapter detection to use lowercase "story" instead of "STORY"
   * Added logging to track chapter type conversions
   * Used default lowercase values when creating new planned chapter types

3. **Created Comprehensive Test Script:**
   * Created `test_summary_button_flow.py` to verify the entire flow from storing a state to retrieving and reconstructing it
   * Added validation to confirm the summary data is correctly formatted
   * Ensured the test creates a state with all required fields
   * Added detailed logging to track the process

### Current Status

Our changes have successfully fixed the issue:

1. **State Storage Works:**
   * The state is being stored successfully with a unique ID
   * The memory cache contains the state ID and data
   * Logging confirms the state is stored correctly

2. **State Retrieval Works:**
   * The summary page can now retrieve the state successfully
   * Case sensitivity in chapter types is handled properly
   * All chapter types are converted to lowercase before creating the AdventureState object
   * The summary page displays correctly with chapter summaries, educational questions, and statistics

3. **Test Script Passes:**
   * The `test_summary_button_flow.py` script passes successfully
   * All chapter types are properly converted to lowercase
   * The state is correctly reconstructed and formatted
   * The summary data is verified to contain all required fields
