# Active Context

## Improved Chapter Summary Generation with Format Examples (2025-03-21)

1. **Fixed Chapter Summary Title and Summary Extraction:**
   * Problem: The LLM wasn't including the expected section headers in its response, causing the parsing function to fail to extract the title and summary
   * Solution:
     - Added clear examples to the prompt showing both incorrect and correct formats
     - Explicitly instructed the LLM to use the exact section headers
     - Made the format requirements more prominent in the prompt
   * Implementation Details:
     - Updated `SUMMARY_CHAPTER_PROMPT` in `prompt_templates.py` to include:
       - An "INCORRECT FORMAT (DO NOT USE)" example showing what not to do
       - A "CORRECT FORMAT (USE THIS)" example showing the proper structure with section headers
       - Clear instructions to use the exact section headers
     - Enhanced the `parse_title_and_summary` function to extract both title and summary from the response
   * Benefits:
     - Reliable extraction of both chapter titles and summaries
     - Consistent formatting across all chapters
     - Better user experience with properly formatted chapter summaries
     - Improved error handling with fallback to defaults when extraction fails

2. **Consolidated Chapter Summary Generation Scripts:**
   * Problem: Separate scripts for standard and React-compatible summary generation led to code duplication and maintenance issues
   * Solution:
     - Integrated React-specific functionality into the main `generate_chapter_summaries.py` script
     - Added command-line flags to control output format and destination
     - Implemented shared core functionality for both standard and React modes
   * Implementation Details:
     - Added `--react-json` flag to generate React-compatible JSON
     - Added `--react-output` flag to specify the output file for React data
     - Implemented `generate_react_summary_data` function to format data for React
     - Reused core summary generation logic for both standard and React modes
   * Benefits:
     - Simplified codebase with a single script for all summary generation needs
     - Consistent summary generation across all output formats
     - Easier maintenance with shared core functionality
     - Flexible command-line options for different use cases

## Fixed React-based SUMMARY Chapter Integration (2025-03-21)

1. **Fixed React Summary App Integration with FastAPI Server:**
   * Problem: The React summary app was not being served properly, resulting in 404 errors
   * Solution:
     - Updated summary_router.py to serve the React app's index.html instead of the test HTML file
     - Configured React Router with proper basename to account for the /adventure prefix
     - Ensured correct path resolution between FastAPI and React app
   * Implementation Details:
     - Modified `summary_router.py` to add `REACT_APP_DIST_DIR` constant and logic to serve the React app index.html
     - Updated the React Router configuration in App.tsx to use the base URL from Vite's configuration
     - Added `basename={import.meta.env.BASE_URL || "/"}` to BrowserRouter component
     - Fixed the route path from '/adventure-summary' to '/summary' to match the expected structure
   * Benefits:
     - React summary app now properly renders at /adventure/summary endpoint
     - Maintained consistent user experience with Learning Reports showing both chosen and correct answers
     - Improved error handling with fallback to test HTML if React app isn't built

## React-based SUMMARY Chapter Implementation (2025-03-20)

1. **Created Modern React-based SUMMARY Chapter:**
   * Problem: The existing typewriter-style summary had limited visual appeal and interactivity
   * Solution:
     - Implemented a React-based summary page using components from celebration-journey-moments-main
     - Created TypeScript interfaces for structured data
     - Developed FastAPI endpoints to serve the React app and data
     - Created data generation scripts that work with simulation state files
   * Implementation Details:
     - Added TypeScript interfaces in `src/lib/types.ts` for type safety
     - Updated `AdventureSummary.tsx` to fetch data from our API endpoint
     - Created `app/routers/summary_router.py` with endpoints for the React app and data
     - Created `tests/simulations/generate_chapter_summaries_react.py` for data generation
     - Added build and run scripts in the tools directory
   * Benefits:
     - More visually appealing and interactive summary experience
     - Better separation of concerns with React components
     - Improved maintainability with TypeScript interfaces
     - Enhanced user experience with animations and visual elements

2. **Structured Data Generation for Summary:**
   * Problem: Needed a way to extract and format chapter summaries, educational questions, and statistics
   * Solution:
     - Created a script to generate structured JSON data from simulation state files
     - Implemented functions to extract educational questions and calculate statistics
     - Added chapter title generation based on content
   * Implementation Details:
     - Created `generate_react_summary_data` function to format data for React
     - Added `extract_educational_questions` function to extract questions and answers
     - Implemented `calculate_statistics` function for adventure metrics
     - Added `generate_chapter_title` function to create titles from content
   * Benefits:
     - Well-structured data for the React components
     - Comprehensive summary with chapters, questions, and statistics
     - Automatic title generation for better readability
     - Reusable data extraction functions

3. **FastAPI Integration for React App:**
   * Problem: Needed a way to serve the React app and data from the FastAPI backend
   * Solution:
     - Created FastAPI routes for serving the React app and data
     - Updated the main application to include the summary router
     - Implemented API endpoints for serving the summary data
   * Implementation Details:
     - Created `/adventure/summary` route to serve the React app
     - Added `/adventure/api/adventure-summary` endpoint for the data
     - Updated `app/main.py` to include the summary router
     - Added error handling and logging for the API endpoints
   * Benefits:
     - Seamless integration with the existing FastAPI application
     - Clear separation between frontend and backend
     - Reusable API endpoints for future enhancements
     - Improved error handling and logging

## Enhanced Typewriter Summary with Improved Mobile Layout (2025-03-19)

1. **Removed Hardcoded Chapter Titles and Comments:**
   * Problem: The summary chapter had hardcoded chapter titles and comments that weren't reusable
   * Solution:
     - Removed the hardcoded `chapterTitles` array from JavaScript
     - Replaced with generic "Chapter X: Recap" format
     - Simplified content extraction methods to use placeholders
     - Removed hardcoded comments and specific content
   * Implementation Details:
     - Updated `showSummary` method to use a generic title format
     - Simplified `extractChoices` and `extractLearnings` methods
     - Added defensive null checks throughout the code
     - Added comprehensive logging for debugging
   * Benefits:
     - More reusable and data-driven component
     - Easier to maintain without hardcoded content
     - Better adaptability to different chapter types and content

2. **Fixed Mobile Display of Vertical Tabs:**
   * Problem: On mobile devices, the vertical tabs were taking up too much screen space
   * Solution:
     - Updated CSS for mobile view to display tabs horizontally
     - Added proper spacing, sizing, and touch-friendly styling
     - Improved the active tab styling for better visibility
   * Implementation Details:
     - Modified media query for screens smaller than 768px
     - Changed flex-direction to row for horizontal layout
     - Added overflow-x: auto for scrollable tabs
     - Added -webkit-overflow-scrolling: touch for momentum scrolling
     - Adjusted tab size and spacing for touch targets
     - Enhanced active tab styling with scale and shadow
   * Benefits:
     - Better use of screen space on mobile devices
     - More intuitive navigation experience
     - Touch-friendly design with appropriate sizing
     - Visually clear active state for better orientation

3. **Added Defensive Programming for Improved Reliability:**
   * Problem: JavaScript errors were occurring when DOM elements weren't found
   * Solution:
     - Added comprehensive null checks throughout the code
     - Implemented detailed error logging
     - Added fallback behavior for missing elements
   * Implementation Details:
     - Added null checks before accessing DOM elements
     - Added detailed console logging for debugging
     - Implemented verbose error messages
     - Added status reporting for key operations
   * Benefits:
     - More robust code that handles edge cases
     - Better error messages for debugging
     - Graceful degradation when elements are missing
     - Improved overall reliability

## Enhanced Typewriter Summary with Handwriting Animation (2025-03-19)

1. **Implemented Two-Stage Experience for Summary Chapter:**
   * Problem: The original implementation showed both the congratulatory message and chapter summaries on the same page, creating a cluttered experience
   * Solution:
     - Implemented a two-stage approach:
       * First stage: Shows only the "Adventure Complete" notification with stars animation
       * Second stage: Shows only the chapter summaries after clicking a button
     - Added smooth transitions between the two stages
   * Implementation Details:
     - Created separate container divs for each stage
     - Added a "View Your Adventure Summary" button that appears after the stars animation
     - Implemented fade animations for transitioning between views
   * Benefits:
     - Cleaner, more focused user experience
     - Better separation of concerns between celebration and content review
     - More dramatic reveal of the adventure summary

2. **Enhanced Animation with Handwriting Effect:**
   * Problem: The basic typewriter animation was underwhelming and lacked visual appeal
   * Solution:
     - Replaced the basic typewriter effect with a handwriting animation
     - Used a handwriting font (Caveat) for a more natural look
     - Implemented character-by-character animation with randomized properties
   * Implementation Details:
     - Added the Caveat font via Google Fonts
     - Created a span for each character with randomized rotation
     - Added special styling for punctuation (bolder, darker)
     - Implemented subtle movement effects that mimic handwriting
   * Benefits:
     - More visually engaging animation
     - Better mimics the feeling of handwritten notes
     - Creates a more personal, organic feel to the summaries

3. **UI Improvements for Better User Experience:**
   * Problem: The UI had unnecessary elements and lacked intuitive navigation
   * Solution:
     - Made the title clickable to return to the main page
     - Removed the "Start New Journey" button
     - Changed the header format from "Chapter X (TYPE)" to "Summary: Chapter X"
     - Increased the animation speed for a more engaging experience
   * Implementation Details:
     - Added a link around the title that points to the main page
     - Removed the button from the HTML and its event listener from JavaScript
     - Updated the header format in both HTML and JavaScript
     - Reduced animation delays and durations for faster rendering
   * Benefits:
     - More intuitive navigation
     - Cleaner interface without unnecessary elements
     - Faster, more engaging animations
     - Better overall user experience

## Updated Chapter Summary Generator for Simulation State JSON Files (2025-03-19)

1. **Updated generate_chapter_summaries.py to Work with Simulation State JSON Files:**
   * Problem: The script was designed to extract chapter content from log files, but now we have simulation state JSON files from the consolidated generate_all_chapters.py script
   * Solution:
     - Modified the script to accept simulation state JSON files instead of log files
     - Updated the chapter content extraction to navigate the JSON structure
     - Added a delay mechanism to prevent API timeouts and connection issues
   * Implementation Details:
     - Updated `load_chapter_content` function to extract chapter content directly from the JSON structure
     - Renamed `find_latest_simulation_log` to `find_latest_simulation_state` to find the latest simulation state JSON file
     - Added a configurable delay parameter with a default of 2.0 seconds between chapter processing
     - Added a command-line argument `--delay` to customize the delay
     - Updated documentation and examples to reflect the new features
   * Benefits:
     - Script now works with the new JSON file format produced by generate_all_chapters.py
     - More reliable operation with the delay mechanism preventing API overload
     - Consistent chapter summary generation for all 10 chapters
     - Better error handling and recovery from API timeouts

## Consolidated Simulation Scripts and Renamed chapter_generator.py (2025-03-19)

1. **Consolidated Simulation Scripts:**
   * Problem: Multiple simulation scripts with overlapping functionality were causing confusion and maintenance issues
   * Solution:
     - Removed redundant simulation scripts:
       * `story_simulation.py`: Replaced by the enhanced chapter_generator.py
       * `generate_all_chapters.py` (old version): Functionality merged into chapter_generator.py
       * `run_chapter_generator.py`: Simple wrapper script no longer needed
       * `batch_generate_chapters.py`: Specialized batch script no longer necessary
     - Renamed `chapter_generator.py` to `generate_all_chapters.py` for consistency
     - Renamed `CHAPTER_GENERATOR_README.md` to `GENERATE_ALL_CHAPTERS.md`
     - Updated documentation to reflect the consolidated approach
   * Implementation Details:
     - Updated file paths and references in the script
     - Changed log filename pattern to match the new script name
     - Updated logger name from "chapter_generator" to "generate_all_chapters"
     - Updated header text in log files
   * Benefits:
     - Simplified codebase with fewer redundant files
     - Clearer naming convention for simulation scripts
     - Improved maintainability with consolidated functionality
     - Reduced confusion for developers working with simulation tools

## Fixed Chapter Generator Script for Simulation State Validation (2025-03-18)

1. **Fixed SimulationState Class in chapter_generator.py:**
   * Problem: The script was failing with `ValueError: "SimulationState" object has no field "simulation_metadata"` because AdventureState (which SimulationState extends) is a Pydantic model that doesn't allow adding arbitrary fields.
   * Solution:
     - Properly defined the simulation_metadata field using Pydantic's Field:
       ```python
       simulation_metadata: Dict[str, Any] = Field(
           default_factory=dict, description="Metadata specific to the simulation run"
       )
       ```
     - Modified the __init__ method to initialize the field properly:
       ```python
       def __init__(self, *args, **kwargs):
           # Initialize with default values
           if "simulation_metadata" not in kwargs:
               kwargs["simulation_metadata"] = {
                   "run_id": run_id,
                   "timestamp": datetime.now().isoformat(),
                   "random_choices": [],
               }
           super().__init__(*args, **kwargs)
       ```
     - Updated the save_to_file method to handle the simulation_metadata field correctly
   * Implementation Details:
     - Added import for Pydantic's Field
     - Added proper type hints for the simulation_metadata field
     - Added null checking in the record_choice method
     - Removed redundant code in the save_to_file method
   * Benefits:
     - Script now runs without validation errors
     - Properly integrates with Pydantic's validation system
     - Maintains the same functionality while following proper OOP principles
     - Provides better type hints for IDE support

2. **Fixed WebSocketClientProtocol Deprecation Warnings:**
   * Problem: The script was generating deprecation warnings for WebSocketClientProtocol
   * Solution:
     - Updated imports to use websockets.client
     - Updated type hints to use websockets.client.WebSocketClientProtocol
   * Implementation Details:
     - Changed import from `import websockets` to `import websockets.client`
     - Updated all function signatures to use the new type:
       ```python
       async def establish_websocket_connection(
           uri: str, retry_count: int = 0
       ) -> Optional[websockets.client.WebSocketClientProtocol]:
       ```
       ```python
       async def send_message(
           ws: websockets.client.WebSocketClientProtocol, message: Dict[str, Any]
       ) -> None:
       ```
       ```python
       async def process_chapter(
           websocket: websockets.client.WebSocketClientProtocol,
           chapter_number: int,
           is_conclusion: bool = False,
       ) -> Tuple[str, List[Dict[str, Any]]]:
       ```
       ```python
       async def process_summary(websocket: websockets.client.WebSocketClientProtocol) -> str:
       ```
   * Benefits:
     - Eliminates deprecation warnings
     - Future-proofs the code against API changes
     - Follows best practices for the websockets library

## New Chapter Summary Generator Script (2025-03-17)

1. **Created Standalone Chapter Summary Generator Script:**
   * Problem: Needed a way to generate consistent chapter summaries for all chapters, including Chapter 10 (CONCLUSION)
   * Solution:
     - Created `tests/simulations/generate_chapter_summaries.py` script that:
       * Extracts chapter content from simulation log files
       * Generates summaries using the same prompt template for all chapters
       * Uses the same function to generate summaries for all chapters (no special cases)
       * Handles missing chapters gracefully by continuing to process available chapters
   * Implementation Details:
     - Uses direct API call to Gemini with fallback to streaming approach
     - Implements retry logic with exponential backoff for reliability
     - Provides both standard and compact output formats
     - Supports skipping JSON file creation with `--no-json` flag
     - Includes detailed error handling and logging
   * Benefits:
     - Consistent summary generation for all chapters, including CONCLUSION
     - Robust error handling that continues processing even if some chapters are missing
     - Flexible output options for different use cases
     - Reliable summary generation with retry logic

## Ongoing Issue: Chapter 10 Content Not Being Captured in Simulation Log (2025-03-18)

1. **Issue with Chapter 10 Content in generate_all_chapters.py:**
   * Problem: Chapter 10 content is visible in the terminal but not being captured in the simulation log file.
   * Current Status:
     - Created `generate_all_chapters.py` script to focus solely on generating all 10 chapters
     - Modified the script to continue processing WebSocket messages after receiving the "story_complete" event
     - Added special handling for timeouts and connection closed events when processing the conclusion chapter
     - Added a new event type `EVENT:CONCLUSION_CHAPTER` to log the conclusion chapter content
   * Observed Behavior:
     - The script successfully processes chapters 1-9
     - It logs "Chapter 10 content complete (3006 chars)" in the terminal
     - It logs "EVENT:STORY_COMPLETE" in the log file
     - It logs "Waiting for conclusion chapter content..." in the log file
     - But then it times out waiting for a response: "Timeout waiting for response in chapter 10"
   * Next Steps:
     - Investigate why the WebSocket connection is being closed or timing out before Chapter 10 content can be fully processed
     - Consider increasing the timeout value for the conclusion chapter
     - Add more detailed logging to track the WebSocket connection state
     - Explore alternative approaches to capture the conclusion chapter content

## Ongoing Issue: Chapter 10 Summary Not Showing in Adventure Summary (2025-03-17)

1. **Partial Fix for WebSocket Connection Closure Issue:**
   * Problem: Chapter 10's summary is still not showing up properly in the adventure summary. The connection now stays open, but we're still seeing a placeholder summary instead of the actual content.
   * Current Status:
     - Modified `websocket_router.py` to keep the connection open after the CONCLUSION chapter
     - Changed the `break` statement to `continue` in the `is_story_complete` condition
     - Added enhanced logging in WebSocket service
     - Increased timeout for summary processing
   * Remaining Issue:
     - Despite these changes, we're still seeing a generic placeholder for Chapter 10:
     ```
     ### Chapter 10 (Conclusion)
     In the conclusion chapter, the adventure reached its resolution. The protagonist faced the final challenge and completed their journey, bringing closure to the story and reflecting on the lessons learned along the way.
     ```
     - This is the default placeholder text, not an actual summary generated from the chapter content
   * Next Steps:
     - Further investigate why the Chapter 10 summary isn't being properly generated or captured
     - Check if the summary generation is happening but not being stored correctly
     - Verify if the CONCLUSION chapter summary is being generated with the correct parameters
     - Ensure the summary is being properly included in the final state

2. **Enhanced Logging in WebSocket Service:**
   * Implementation Details:
     - Added logs for current state: `logger.info(f"Current state has {len(state.chapters)} chapters")`
     - Added logs for chapter summaries: `logger.info(f"Current chapter summaries: {len(state.chapter_summaries)}")`
     - Added logs for CONCLUSION chapter: `logger.info(f"Found CONCLUSION chapter: {conclusion_chapter.chapter_number}")`
     - Added logs for summary generation: `logger.info(f"Generated CONCLUSION chapter summary: {chapter_summary[:100]}...")`
   * Benefits:
     - Better visibility into the summary generation process
     - Easier debugging of issues with chapter summaries
     - More detailed error information when problems occur

3. **Increased Timeout for Summary Processing:**
   * Implementation Details:
     ```python
     # Added new constant
     SUMMARY_TIMEOUT = 120  # seconds specifically for summary operations
     
     # Used longer timeout for summary response
     response_raw = await asyncio.wait_for(
         websocket.recv(), timeout=SUMMARY_TIMEOUT
     )
     ```
   * Benefits:
     - Prevents timeouts during summary generation
     - Allows for more complex summary processing
     - Improves reliability of the simulation tests

## Refactored Story Simulation for Improved Maintainability (2025-03-17)

1. **Refactored `story_simulation.py` for Better Maintainability:**
   * Problem: The story simulation code had duplicate sections, inconsistent chapter summary logging, and complex nested logic
   * Solution:
     - Created dedicated helper functions for common operations
     - Standardized chapter summary logging with a single function
     - Consolidated verification steps for chapter summaries
     - Added specific error types for better error handling
   * Implementation Details:
     - Created `log_chapter_summary` function to standardize all chapter summary logging
     - Implemented `verify_chapter_summaries` function to check for missed summaries
     - Added `establish_websocket_connection` function with proper retry logic
     - Created `send_message` function for consistent WebSocket message sending
     - Added specific error types: `WebSocketConnectionError`, `ResponseTimeoutError`, `ResponseParsingError`
   * Benefits:
     - Improved maintainability with more modular code
     - Better debugging with source tracking for chapter summaries
     - Reduced code duplication for common operations
     - More consistent approach to chapter summary handling
     - Enhanced error handling with specific error types

## Standardized Chapter Summary Logging and Extraction (2025-03-16)

1. **Standardized Chapter Summary Logging in `story_simulation.py`:**
   * Problem: Chapter summaries were logged inconsistently, with the conclusion chapter (Chapter 10) using a different format than regular chapters
   * Solution:
     - Standardized all chapter summary logging to use the `EVENT:CHAPTER_SUMMARY` format
     - Implemented consistent debug logging with `"Chapter {chapter_number} summary: {content}"` format
     - Added verification steps to ensure all chapter summaries are properly logged
     - Added multiple fallback mechanisms to retroactively log any missed summaries
   * Implementation Details:
     - Modified the `summary_complete` handler to explicitly log all chapter summaries with `EVENT:CHAPTER_SUMMARY`
     - Added a verification step that checks for any missing chapter summaries
     - Added a final verification at the end of simulation to catch any remaining unlogged summaries
     - Standardized debug logging format for all chapters including the conclusion
   * Benefits:
     - Consistent logging format for all chapters (1-10) makes debugging easier
     - Multiple verification steps ensure no chapter summaries are missed
     - Improved reliability for testing and analysis tools that depend on log data
     - Better maintainability with standardized logging patterns

2. **Enhanced Chapter Summary Extraction in `show_summary_from_log.py`:**
   * Problem: The extraction script wasn't reliably finding Chapter 10 summaries due to inconsistent logging formats
   * Solution:
     - Prioritized `EVENT:CHAPTER_SUMMARY` as the primary standardized format
     - Implemented a fallback hierarchy with clear source tracking
     - Added support for both old and new logging formats
     - Added tracking of which chapters have been found to avoid duplicates
   * Implementation Details:
     - Added tracking of found chapters using a `found_chapters` set
     - Implemented a prioritized extraction approach:
       1. First try `EVENT:CHAPTER_SUMMARY` (primary standardized format)
       2. Then try `STORY_COMPLETE` event (fallback)
       3. Then try `FINAL_CHAPTER_SUMMARIES` event (fallback)
       4. Finally try direct content extraction (last resort fallback)
     - Added clear logging to show which source each chapter summary came from
     - Added support for both old "Final chapter content" and new "Chapter X summary" formats
   * Benefits:
     - More reliable extraction of all chapter summaries, including Chapter 10
     - Clear visibility into which source each summary came from
     - Backward compatibility with existing log files
     - Prioritization of the standardized format for better consistency

## Updated Story Simulation for Complete Chapter Summaries (2025-03-16)

1. **Enhanced Story Simulation for CONCLUSION Chapter Summary:**
   * Problem: The simulation was ending prematurely after the CONCLUSION chapter, before the CONCLUSION chapter summary could be generated
   * Solution:
     - Modified the "story_complete" handler to send a "reveal_summary" choice instead of immediately returning
     - Added handlers for "summary_start" and "summary_complete" message types
     - Enhanced logging for SUMMARY chapter content and events
     - Added "EVENT:FINAL_CHAPTER_SUMMARIES" log entry for the complete set of summaries
   * Implementation Details:
     - After receiving the "story_complete" message, the simulation now sends a "reveal_summary" choice
     - This simulates the user clicking the "Reveal Your Adventure Summary" button
     - The simulation then processes the SUMMARY chapter and captures all 10 chapter summaries
     - New log events track the summary generation process
   * Benefits:
     - All 10 chapter summaries (including CONCLUSION) are now captured in the simulation log
     - The simulation accurately reflects the complete user journey through the application
     - Provides comprehensive test data for verifying the chapter summary functionality
     - Ensures the SUMMARY chapter is properly tested in automated simulations

## Improved CONCLUSION Chapter Summary Generation (2025-03-16)

1. **Consistent Chapter Summary Generation for All Chapters:**
   * Problem: The CONCLUSION chapter didn't have a chapter summary to be used in the SUMMARY chapter
   * Solution:
     - Modified the client-side code in `index.html` to send a choice message with ID "reveal_summary" instead of a "request_summary" message
     - Enhanced `process_choice()` in `websocket_service.py` to handle this special choice ID and generate a summary for the CONCLUSION chapter
     - Removed the special handling for "request_summary" messages in `websocket_router.py`
     - Removed the `process_summary_request()` function from `websocket_service.py`
   * Implementation Details:
     - When the "Reveal Your Adventure Summary" button is clicked, it now sends a choice with ID "reveal_summary"
     - This choice is processed by `process_choice()` which generates a summary for the CONCLUSION chapter using `chapter_manager.generate_chapter_summary()`
     - The summary is stored in `state.chapter_summaries` just like all other chapter summaries
     - The SUMMARY chapter is then created and displayed with all chapter summaries, including the CONCLUSION chapter
   * Benefits:
     - Consistent chapter summary generation for all chapters, including the CONCLUSION chapter
     - Complete adventure recap in the SUMMARY chapter
     - Simplified architecture with a single code path for all chapter summaries
     - Improved maintainability with less special-case handling
