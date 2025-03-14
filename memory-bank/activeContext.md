# Active Context

## Enhanced Chapter Summary Generation with Educational Context (2025-03-16)

1. **Completely Redesigned SUMMARY_CHAPTER_PROMPT Template:**
   * Problem: Previous chapter summaries lacked educational context and didn't emphasize the choices made
   * Solution:
     - Implemented a completely redesigned SUMMARY_CHAPTER_PROMPT with a more structured format:
     ```python
     SUMMARY_CHAPTER_PROMPT = """
     This is one chapter from a Choose Your Own Adventure story. At the end of each chapter, the user is presented with choices.
     Combine CHAPTER CONTENT and CHOICE MADE to create a natural, organic and concise summary (70-100 words) of that captures the key narrative events and character development.

     The summary should be written in third person, past tense, and maintain the adventure's narrative tone. 
     If there are educational questions relating to CHOICE MADE, quote the entire question without paraphrasing it. 
     This summary will be used together with future chapter summaries as a recap to the whole adventure spanning multiple chapters.

     # CHAPTER CONTENT
     {chapter_content}

     # CHOICE MADE
     "{chosen_choice}" - {choice_context}

     # CHAPTER SUMMARY
     """
     ```
     - Increased summary length from 30-40 words to 70-100 words for more comprehensive recaps
     - Added explicit instructions to quote educational questions verbatim
     - Added clear section headings for better prompt organization

2. **Added Choice Context for Educational Feedback:**
   * Implementation Details:
     - Added `choice_context` parameter to `generate_chapter_summary` method in `chapter_manager.py`
     - Updated `process_choice` function in `websocket_service.py` to construct appropriate context:
       * For LESSON chapters: " (Correct answer)" or " (Incorrect answer)" based on response
       * For STORY chapters: No additional context (empty string)
     - Added error handling to ensure the main flow continues even if summary generation fails

3. **Enhanced Debugging for Chapter Summary Generation:**
   * Added comprehensive debug logging in `generate_chapter_summary` method:
     ```python
     logger.debug(f"\n=== DEBUG: Full SUMMARY_CHAPTER_PROMPT sent to LLM ===\n{custom_prompt}\n===================================\n")
     ```
   * This allows developers to see the exact prompt sent to the LLM, including all substituted values

4. **Benefits of the New Implementation:**
   * More detailed and comprehensive chapter summaries (70-100 words vs. 30-40 words)
   * Educational content is preserved with verbatim question quoting
   * Feedback on correct/incorrect answers is included for educational chapters
   * Improved narrative flow with better context from choices made
   * Extensible design that can accommodate future chapter types
   * Easier debugging with comprehensive logging

## Separated Image Scene Generation from Chapter Summaries (2025-03-15)

1. **Implemented Dedicated Image Scene Generation:**
   * Problem: The application was using chapter summaries for both narrative recaps and image generation, creating a compromise between two different needs
   * Root Cause:
     - Chapter summaries needed to be comprehensive narrative overviews (30-40 words covering key events and educational content)
     - Image generation needs vivid visual scenes focused on the most dramatic or visually compelling moments (20-30 words of pure visual description)
     - Using the same text for both purposes created sub-optimal results for one or both uses
   * Solution:
     - **Added New Template in `prompt_templates.py`:**
       * Created `IMAGE_SCENE_PROMPT` specifically for extracting the most visually compelling moment from a chapter:
       ```python
       IMAGE_SCENE_PROMPT = """Identify the single most visually striking moment from this chapter that would make a compelling illustration. 

       Focus on:
       1. A specific dramatic action or emotional peak
       2. Clear visual elements (character poses, expressions, environmental details)
       3. The moment with the most visual energy or emotional impact
       4. Elements that best represent the chapter's theme or turning point

       Describe ONLY this scene in 20-30 words using vivid, specific language. Focus purely on the visual elements and action, not narrative explanation. Do not include character names or story title.

       CHAPTER CONTENT:
       {chapter_content}

       SCENE DESCRIPTION:
       """
       ```
     - **Added New Method in `ChapterManager`:**
       * Created `generate_image_scene` method that uses the new prompt to extract the most visually striking moment
       * Implemented similar structure to `generate_chapter_summary` but with different focus
       * Added robust error handling and fallback mechanisms
     - **Updated WebSocket Service:**
       * Modified `stream_and_send_chapter` to use `generate_image_scene` instead of `generate_chapter_summary` for image generation
       * Kept the same `enhance_prompt` mechanism to add agency, story, and visual details
   * Implementation Details:
     - Maintained parameter compatibility with existing `enhance_prompt` method
     - Used the same LLM approach but with different prompt instructions
     - Added comprehensive logging for debugging
     - Implemented robust fallback mechanism when image scene generation fails
   * Result:
     - Chapter summaries now focus on comprehensive narrative overviews (better for SUMMARY chapter)
     - Image generation now focuses on the most visually compelling moments (better for illustrations)
     - More dynamic, exciting illustrations that capture specific dramatic moments
     - Clearer separation of concerns between the two different needs

## Removed Chapter Summary Truncation for Complete Summaries (2025-03-15)

1. **Removed Chapter Summary Truncation:**
   * Problem: Chapter summaries were being artificially truncated to 40 words when they exceeded 50 words, causing incomplete summaries ending with "..."
   * Root Cause:
     - The `generate_chapter_summary` method in `ChapterManager` had explicit truncation logic:
     ```python
     # Truncate if needed
     if len(summary.split()) > 50:
         summary = " ".join(summary.split()[:40]) + "..."
     ```
     - This was causing summaries like the one in Chapter 8 to be cut off with "Maya resolved to..."
   * Solution:
     - Removed the truncation logic from the `generate_chapter_summary` method
     - Maintained the LLM prompt that still guides it to generate concise summaries
     - Kept the empty summary check and fallback mechanism
   * Implementation Details:
     - Removed the code block that checked for summaries longer than 50 words
     - Removed the code that truncated summaries to 40 words and added "..."
     - Kept the logging of summary generation
   * Result:
     - Chapter summaries are now displayed in full as generated by the LLM
     - No more truncated summaries ending with "..."
     - More complete and informative chapter summaries throughout the application
     - Better context in the summary chapter where these summaries are displayed

## Fixed Simulation Log Summary Extraction for Complete Chapter Summaries (2025-03-15)

1. **Fixed Chapter Summary Extraction from Simulation Logs:**
   * Problem: The `show_summary_from_log.py` script wasn't extracting all chapter summaries from simulation logs, resulting in dummy summaries for chapters 9-10
   * Root Causes:
     - The script wasn't extracting summaries from the STORY_COMPLETE event in the log file
     - Chapter 10 (conclusion) content was generated after the STORY_COMPLETE event
     - The extraction logic wasn't handling the different event types and formats properly
   * Solution:
     - **Enhanced `extract_chapter_summaries_from_log` in `debug_summary_chapter.py`:**
       * Added code to extract summaries from the STORY_COMPLETE event
       * Fixed logger variable scope issues for proper error handling
       * Added detailed logging to track where summaries are found
     - **Enhanced `show_summary_from_log.py` script:**
       * Added code to extract chapter summaries from the STORY_COMPLETE event
       * Added code to extract chapter 10 content from the "Final chapter content" message
       * Implemented summary generation for chapter 10 using the first few sentences
       * Improved mapping of summaries to their respective chapter numbers
   * Reference: For details on the story simulation structure, see the "Story Simulation Structure" section in systemPatterns.md
   * Verification:
     - Successfully extracted all 9 chapter summaries from the STORY_COMPLETE event
     - Successfully generated a summary for chapter 10 from the "Final chapter content" message
     - Properly displayed all 10 chapter summaries in the summary chapter
     - Included all 3 educational questions in the Learning Report section
   * Result:
     - The script now correctly extracts all chapter summaries from simulation logs
     - No more dummy summaries for chapters 9-10
     - Complete summary chapter with all 10 chapters and educational questions
     - Better understanding of the story simulation structure for future development

## Improved Chapter Summaries with Narrative Focus (2025-03-14)

1. **Enhanced Chapter Summary Generation:**
   * Problem: Chapter summaries were optimized for image generation (visual scenes) rather than narrative progression, making the SUMMARY chapter less cohesive and educational
   * Root Cause:
     - The hardcoded prompt in `generate_chapter_summary()` was focused on "vivid visual scene" descriptions
     - Summaries excluded dialogue and abstract concepts, focusing only on visual elements
     - The 20-word limit constrained the ability to capture educational content and character development
   * Solution:
     - **Created New Prompt Template:**
       * Added `SUMMARY_CHAPTER_PROMPT` to `app/services/llm/prompt_templates.py`
       * Designed the prompt to focus on narrative events, character development, and educational content
       * Increased word count guidance to 30-40 words for more comprehensive summaries
     - **Updated Image Generation Service:**
       * Imported the new prompt template in `app/services/image_generation_service.py`
       * Replaced the hardcoded visual-focused prompt with the narrative-focused template
       * Maintained the same LLM service call structure for compatibility
   * Verification:
     - Analyzed simulation logs to confirm chapter summaries are being generated
     - Verified the summaries now include narrative elements and educational content
   * Result:
     - Chapter summaries now capture key story events and character development
     - Summaries include important choices and educational content when present
     - Consistent third-person, past tense voice throughout all summaries
     - The SUMMARY chapter provides a more cohesive and educational recap of the adventure

## Enhanced Simulation Log Summary Viewer with Educational Questions (2025-03-14)

1. **Enhanced Simulation Log Summary Viewer:**
   * Problem: The `show_summary_from_log.py` script was not extracting chapter summaries from simulation logs and was showing dummy summaries instead. Additionally, educational questions encountered during the adventure were not being displayed in the Learning Report section.
   * Root Causes:
     - The script wasn't properly extracting chapter content from STATE_TRANSITION events in the log file
     - No mechanism to extract educational questions from the log file
     - The AdventureState model didn't have a field to store lesson questions
   * Solution:
     - **Enhanced Chapter Summary Extraction:**
       * Modified `extract_chapter_summaries_from_log` to extract chapter content from STATE_TRANSITION events
       * Added support for different content formats (direct content field and chapter_content.content)
       * Implemented fallback to use the first paragraph of chapter content as a summary
     - **Added Lesson Question Extraction:**
       * Updated `extract_chapter_summaries_from_log` to extract educational questions from EVENT:LESSON_QUESTION entries
       * Added a `lesson_questions` field to the AdventureState model to store the questions
       * Enhanced the summary display to show questions, topics, and correct answers
     - **Improved Summary Display:**
       * Added handling for cases with fewer than 10 summaries by adding dummy summaries for missing chapters
       * Replaced the default "You didn't encounter any educational questions" message with actual questions
       * Formatted the Learning Report section to display educational content
   * Verification:
     - Tested with multiple simulation log files
     - Successfully extracted chapter summaries and lesson questions
     - Properly displayed the Learning Report section with educational questions
   * Result:
     - The script now correctly extracts chapter summaries from simulation logs
     - Educational questions are displayed in the Learning Report section
     - The summary provides a complete overview of the adventure, including both narrative and educational content

2. **Fixed SUMMARY Chapter Functionality:**
   * Problem: After clicking the "Reveal Your Adventure Summary" button at the end of a 10-chapter adventure, the application showed a loading spinner but never actually loaded the summary page.
   * Root Causes:
     - State synchronization issue: The backend wasn't properly receiving the state from the client when processing summary requests
     - Error handling: There was no proper error handling or timeout detection in the frontend
   * Solution:
     - **Backend Fix in `websocket_service.py`**:
       * Modified the `process_summary_request` function to properly receive and update the state from the client
       * Added code to get the client's state from the request and update the state manager
       * Improved error handling to provide better feedback when issues occur
     - **Frontend Fix in `index.html`**:
       * Enhanced the `requestSummary` function with better error handling and a timeout
       * Added code to clear content and reset state before sending the request
       * Implemented a 10-second timeout to detect if the request is hanging
       * Added better error messaging for users
   * Verification:
     - Created two debug scripts to test the functionality:
       * `tests/debug_summary_chapter.py` - Tests the summary content generation
       * `tests/debug_websocket_router.py` - Tests the WebSocket router handling of summary requests
     - Both scripts successfully generate and display summary content
   * Result:
     - The "Reveal Your Adventure Summary" button now works correctly
     - Users can see the summary page after completing an adventure
     - Better error handling and user feedback if issues occur

## Updated Story Simulation for Chapter Summaries Support (2025-03-11)

1. **Enhanced Story Simulation for Chapter Summaries Testing:**
   * Purpose: Update the story simulation to support the new chapter summaries approach
   * Implementation Details:
     - Updated initial state structure to include the `chapter_summaries` field
     - Added detection and logging of chapter summaries as they're received from the server
     - Implemented structured logging for chapter summary events with "EVENT:CHAPTER_SUMMARY" prefix
     - Added a comprehensive log at the end of simulation with all chapter summaries
     - Enhanced human-readable output with chapter summary display
     - Added detailed usage instructions to the file
   * Technical Approach:
     - Modified the initial state message to include an empty `chapter_summaries` array
     - Added logic to detect and log chapter summaries in the state updates from the server
     - Implemented structured logging with event types like "EVENT:CHAPTER_SUMMARIES_UPDATED" and "EVENT:CHAPTER_SUMMARY"
     - Added a final "EVENT:ALL_CHAPTER_SUMMARIES" log at the end of the simulation
     - Added a human-readable display of all chapter summaries at the end of the run
   * Benefits:
     - Enables testing of the SUMMARY chapter functionality without manually going through all 10 chapters
     - Provides structured data for automated testing of the chapter summaries feature
     - Captures chapter summaries in a format that can be easily extracted and analyzed
     - Maintains alignment with how chapter summaries are implemented in the actual application
   * Usage:
     - Run the simulation with `python tests/simulations/story_simulation.py`
     - Check the generated log file for chapter summaries
     - Extract the summaries from the "EVENT:ALL_CHAPTER_SUMMARIES" log entry
     - Use the summaries to test the SUMMARY chapter implementation independently

## Fixed Bug: Paragraph Formatter Using Incomplete Text (2025-03-10)

1. **Fixed Paragraph Formatter Bug:**
   * Problem: Paragraph formatter was detecting text without proper paragraph formatting, but only reformatting the initial buffer (first ~1000 characters) instead of the full response
   * Root Cause:
     - In both OpenAIService and GeminiService, when text needed formatting, the system was passing `collected_text` (initial buffer) to the reformatting function instead of `full_response` (complete text)
     - This resulted in properly formatted initial text but the remainder of the response still lacked paragraph breaks
     - Debug logs showed the detection was working, but the reformatted text wasn't being fully utilized
   * Solution:
     - Modified all instances in both service classes to use `full_response` instead of `collected_text` when reformatting is needed
     - Updated the code in OpenAIService.generate_with_prompt, OpenAIService.generate_chapter_stream, GeminiService.generate_with_prompt, and GeminiService.generate_chapter_stream
     - Maintained the existing retry mechanism (up to 3 attempts with progressively stronger formatting instructions)
   * Implementation Details:
     - The fix was a simple but critical change from `collected_text` to `full_response` in the reformatting function calls
     - No changes were needed to the paragraph detection logic or the reformatting function itself
     - The existing retry mechanism and logging were preserved
   * Result:
     - Complete LLM responses now have proper paragraph formatting throughout the entire text
     - Improved readability for users, especially for longer responses
     - Maintained the streaming experience when formatting isn't needed
     - Fixed the issue where debug logs showed detection and reformatting but the output still lacked proper formatting

## Enhanced Summary Implementation with Progressive Chapter Summaries (2025-03-11)

1. **Enhanced Summary Implementation:**
   * Purpose: Improve the SUMMARY chapter by generating and storing chapter summaries throughout the adventure
   * User Experience: 
     - Same button at the end of the CONCLUSION chapter leads to a summary page
     - Summary now shows a chronological recap with detailed summaries of each chapter
     - Learning report still displays questions, answers, and explanations
     - Provides a more detailed and journey-like conclusion to the adventure
   * Implementation Completed:
     - **Backend Model Updates**
       * Added `chapter_summaries` field to the AdventureState model to store summaries
       * Maintained compatibility with existing SUMMARY chapter type
     
     - **Backend Services Implementation**
       * Modified `process_choice` function to generate chapter summaries after each choice
       * Completely rewrote `generate_summary_content` function to use stored summaries
       * Maintained the existing `process_summary_request` function
       * Added error handling to ensure the main flow continues even if summary generation fails
     
     - **Integration with Existing Systems**
       * Leveraged the existing `generate_chapter_summary` method from ImageGenerationService
       * Reused the same summary generation logic that's already used for image prompts
       * Added fallback to the original LLM-based summary generation if no summaries are available
     
     - **Technical Advantages**
       * Distributed processing - summaries generated throughout the adventure
       * More resilient - if one chapter summary fails, others can still be displayed
       * Reduced wait time at the end of the adventure
       * Better captures "in-the-moment" details that might be lost in a retrospective summary
   
   * Design Principles Applied:
     - Maintained consistent visual theming with the existing app
     - Created a more detailed chronological recap of the adventure journey
     - Preserved chapter context by showing chapter numbers and types
     - Maintained the same learning report format for educational value
     - Improved reliability through distributed processing

   * Educational Value for Parents:
     - More detailed visualization of the child's journey through each chapter
     - Clearer connections between specific chapters and learning moments
     - Same comprehensive documentation of questions, answers, and explanations
     - Better captures the evolution of the story and learning progression

   * Technical Implementation Details:
     - Added chapter_summaries field to AdventureState model
     - Modified process_choice to generate and store summaries asynchronously
     - Rewrote generate_summary_content to use stored summaries
     - Added fallback to original LLM-based summary if needed
     - Maintained backward compatibility with existing summary functionality

## Recent Enhancement: Fixed Chapter Summary Generation for Image Prompts (2025-03-10)

1. **Fixed Chapter Summary Generation for Image Prompts:**
   * Problem: Chapter summaries generated by the LLM weren't being included in image generation prompts
   * Root Cause:
     - Mismatch between how the streaming response was being collected from different LLM providers
     - The Gemini API's streaming response wasn't being properly captured in the async for loop
     - The summary was being generated but then lost or misinterpreted as empty
   * Solution:
     - Implemented service-specific handling for different LLM providers:
       - For Gemini: Used direct API call instead of streaming for summary generation
       - For OpenAI: Maintained the streaming approach which works correctly
     - Added comprehensive logging to track the raw response, its length, and processed summary
     - Enhanced empty check to consider very short summaries (less than 5 characters) as empty
     - Improved fallback mechanism to use the first paragraph of chapter content when needed
   * Implementation Details:
     - Added detection of which LLM service is being used (Gemini or OpenAI)
     - Used a more robust approach to collecting chunks from streaming responses
     - Added explicit error handling with graceful fallbacks
     - Implemented detailed logging at each step of the process
   * Key Learning:
     - Different LLM service providers require different implementation approaches for the same functionality
     - Streaming responses work differently between OpenAI and Gemini APIs
     - Direct API calls are more reliable than streaming for short, single-response use cases
     - Always implement robust fallback mechanisms for LLM-dependent features
   * Result:
     - Chapter summaries are now properly included in image generation prompts
     - More relevant and contextual images for each chapter
     - Consistent inclusion of agency choice from Chapter 1 in all images
     - Improved reliability with better error handling and logging

## Recent Enhancement: Paragraph Formatting for LLM Responses (2025-03-09)

1. **Implemented Paragraph Formatting for LLM Responses:**
   * Problem: LLM responses occasionally lacked proper paragraph breaks, causing text to render as one continuous paragraph
   * Solution:
     - Created a new `paragraph_formatter.py` module with functions to detect and fix text without proper paragraph formatting
     - Implemented `needs_paragraphing()` function to detect text that needs formatting based on length, existing paragraph breaks, sentence count, and dialogue markers
     - Added `reformat_text_with_paragraphs()` function that uses the same LLM service to add proper paragraph breaks
     - Implemented multiple retry attempts (up to 3) with progressively stronger formatting instructions
     - Modified both OpenAIService and GeminiService to check for paragraph formatting needs and apply reformatting when necessary
     - Added comprehensive logging of prompts and responses for debugging
   * Implementation Details:
     - Buffer-based approach: Collects initial text buffer to check formatting needs
     - If formatting needed, collects full response before reformatting
     - If not needed, streams text normally for better user experience
     - Tracks full response regardless of formatting needs for proper logging
     - Uses the same LLM service that generated the original content for reformatting
     - Verifies reformatted text contains paragraph breaks before returning
   * Result:
     - Ensures all LLM responses have proper paragraph formatting for better readability
     - Maintains streaming experience when formatting isn't needed
     - Provides detailed logging for monitoring and debugging
     - Gracefully handles cases where reformatting fails

## Recent Enhancement: Fixed Chapter Image Display on Desktop (2025-03-09)

1. **Fixed Chapter Image Display on Desktop:**
   * Problem: Chapter images were being cropped on desktop but displaying correctly on mobile
   * Solution:
     - Changed `object-fit` from "cover" to "contain" to preserve the image's aspect ratio
     - Kept `overflow: hidden` to prevent layout issues
     - Increased the max-height for desktop from 450px to 600px
     - Added additional margin between the image and choice buttons
   * Implementation Details:
     - Modified CSS in `app/static/css/components.css` to ensure proper image display
     - Used media queries to apply different styles for desktop and mobile
     - Maintained consistent styling and animations
   * Result:
     - Images now display correctly on both desktop and mobile
     - Full image is visible without cropping on all devices
     - Proper spacing between image and choice buttons
     - Consistent user experience across all device sizes

## Recent Enhancement: Improved Chapter Image Positioning (2025-03-09)

1. **Moved Chapter Image Position:**
   * Problem: Chapter images were displayed at the top of content, causing children to wait for images before reading
   * Solution:
     - Moved the `<div id="chapterImageContainer">` element in index.html to appear after the story content but before the choices container
     - Added a mb-6 margin-bottom class to ensure proper spacing between the image and the choice buttons
     - Kept all existing functionality intact, including the fade-in animation and asynchronous loading
   * Benefits for Young Users (Ages 6-12):
     - Immediate Engagement - Children can start reading text immediately without waiting for image generation
     - Reduced Perceived Delay - The delay in image loading becomes less noticeable when they're already engaged with the story content
     - Better Narrative Flow - The image now serves as a visual summary of what they've just read, reinforcing the content
     - Natural Reading Pattern - Follows a more natural "read first, then see illustration" pattern common in children's books
     - Smoother Transition - Creates a visual break between the story content and choice selection
   * Result:
     - More effective layout for children in the 6-12 age range
     - Allows children to start reading immediately while the image is being generated in the background
     - Creates a more seamless and engaging experience
     - No changes required to server-side code or image generation logic

## Recent Enhancement: Images for Every Chapter (2025-03-09)

1. **Added Images for Every Chapter:**
   * Problem: Images were only shown for the first chapter's agency choices
   * Solution:
     - Modified `ImageGenerationService` to generate images for all chapters
     - Added `generate_chapter_summary` method to create visual summaries from previous chapter content
     - Updated `enhance_prompt` to handle chapter summaries as input for image generation
     - Modified `stream_and_send_chapter` in `websocket_service.py` to generate images for all chapters
     - Added a new message type (`chapter_image_update`) for sending chapter images to the client
     - Updated the frontend to display chapter images at the top of each chapter
   * Implementation Details:
     - Used the LLM to generate concise visual summaries of previous chapter content
     - Combined summaries with agency choice and story elements to create image prompts
     - Generated images asynchronously to avoid blocking story progression
     - Added smooth fade-in animations for chapter images
   * Result:
     - Every chapter now has a relevant image at the top
     - Images are generated based on the content of the current chapter (better for children aged 6-12)
     - Agency choices are consistently referenced in the images
     - Enhanced visual storytelling experience throughout the adventure

## Recent Enhancement: Landing Page Integration (2025-03-09)

1. **Integrated Landing Page:**
   * Implementation:
     - Created a responsive landing page at `app/static/landing/index.html` with modern design and animations
     - Updated web router in `app/routers/web.py` to serve the landing page at the root URL (/)
     - Configured navigation between landing page and adventure selection page (/adventure)
   * Features:
     - Modern, visually appealing design with animations and clean layout
     - Sections for "How It Works", "Features", and "Adventure Preview"
     - Multiple "Start your adventure" buttons linking to the adventure selection page
     - Fully responsive design for both desktop and mobile devices
   * User Flow:
     - Users first see the landing page when visiting the site
     - Landing page explains the concept and benefits of the educational adventure app
     - Clicking any "Start your adventure" button takes users to the adventure selection page

## Recent Enhancement: Topic Introduction in Lesson Chapters (2025-03-09)

1. **Improved Topic Introduction in Lesson Chapters:**
   * Problem: LESSON_CHAPTER_PROMPT was directly referencing the specific question in the topic introduction
   * Solution:
     - Modified template in `prompt_templates.py` to use `{topic}` instead of directly referencing the question
     - Updated `build_lesson_chapter_prompt` function in `prompt_engineering.py` to pass the topic parameter when formatting the template
   * Result:
     - Lesson chapters now introduce the broader topic (like "Farm Animals" or "Singapore History") rather than directly referencing the specific question
     - Creates a more natural flow for educational content by introducing the broader topic area first before narrowing down to the specific question
     - Uses the topic value that's already available in the lesson data from CSV files

## Recent Enhancement: Explanation Integration in Learning Impact (2025-03-08)

1. **Enhanced Learning Impact with Explanation Integration:**
   * Problem: CORRECT_ANSWER_CONSEQUENCES and INCORRECT_ANSWER_CONSEQUENCES templates weren't using the explanation column from lesson data
   * Solution:
     - Modified templates in `prompt_templates.py` to include the explanation in the learning impact section
     - Updated `process_consequences` function in `prompt_engineering.py` to extract and pass the explanation from lesson data
   * Result:
     - When a student answers a question, the prompt now includes the specific explanation from the lesson data
     - Provides more context for learning moments, especially for incorrect answers
     - Helps the LLM create more educational content with accurate explanations
     - Example: For the Singapore riots question, it now includes the detailed explanation about ethnic tensions and political conflicts

## Development Tools

1. **Code Complexity Analyzer (`tools/code_complexity_analyzer.py`):**
   * Identifies files that may need refactoring due to excessive code size
   * Counts total lines, non-blank lines, and code lines (excluding comments)
   * Supports filtering by file extension and sorting by different metrics
   * Command-line usage: `python tools/code_complexity_analyzer.py [options]`
   * Options:
     - `-p, --path PATH`: Repository path (default: current directory)
     - `-e, --extensions EXT`: File extensions to include (e.g., py js html)
     - `-s, --sort TYPE`: Sort by total, non-blank, or code lines
     - `-n, --number N`: Number of files to display

## Core Architecture

1. **Adventure Flow (`app/routers/web.py`, `app/services/chapter_manager.py`):**
   * ChapterType enum: LESSON, STORY, REFLECT, CONCLUSION
   * Content sources in `prompt_engineering.py`:
     - LESSON: Lessons from `app/data/lessons/*.csv` + LLM wrapper
     - STORY: Full LLM generation with choices
     - REFLECT: Narrative-driven follow-up to LESSON
     - CONCLUSION: Resolution without choices

2. **Chapter Sequencing (`chapter_manager.py`):**
   * First chapter: STORY
   * Second-to-last chapter: STORY
   * Last chapter: CONCLUSION
   * 50% of remaining: LESSON (subject to available questions)
   * 50% of LESSON chapters: REFLECT (follow LESSON)
   * STORY chapters follow REFLECT chapters
   * No consecutive LESSON chapters

3. **State Management (`adventure_state_manager.py`):**
   * Robust choice validation
   * State consistency preservation
   * Error recovery mechanisms
   * Metadata tracking for agency, elements, and challenge types

4. **Story Data Management (`app/data/story_loader.py`):**
   * Loads individual story files from `app/data/stories/` directory
   * Combines data into a consistent structure
   * Provides caching for performance optimization
   * Offers methods for accessing specific story categories

5. **Lesson Data Management (`app/data/lesson_loader.py`):**
   * Loads lesson data exclusively from individual CSV files in `app/data/lessons/` directory
   * Uses pandas' built-in CSV parsing with proper quoting parameters
   * Handles various file encodings (utf-8, latin1, cp1252)
   * Standardizes difficulty levels to "Reasonably Challenging" and "Very Challenging"
   * Provides case-insensitive methods to filter lessons by topic and difficulty
   * Implements robust topic matching with fallback strategies
   * Supports caching for performance optimization
   * Includes detailed logging for debugging

## Recent Changes

### Enhanced Learning Impact with Explanation Integration (2025-03-08)
- Problem: The CORRECT_ANSWER_CONSEQUENCES and INCORRECT_ANSWER_CONSEQUENCES templates weren't using the explanation column from lesson data
- Solution:
  * Modified templates in `prompt_templates.py` to include the explanation:
    ```python
    INCORRECT_ANSWER_CONSEQUENCES = """## Learning Impact
    - Acknowledge the misunderstanding about {question}
    - Create a valuable learning moment from this correction: "{explanation}"
    - Show how this new understanding affects their approach to challenges"""
    ```
  * Updated `process_consequences` function in `prompt_engineering.py` to extract and pass the explanation from lesson data
- Result:
  * When a student answers a question incorrectly, the prompt now includes the specific explanation from the lesson data
  * For example, if a student incorrectly answers a question about the 1964 Singapore riots, the prompt will include the detailed explanation about ethnic tensions and political conflicts
  * This provides more context for the learning moment and helps the LLM create more educational content

### Fixed Question Placeholder in REFLECT Chapters (2025-03-08)
- Problem: The `{question}` placeholder in the exploration_goal wasn't being properly replaced in REFLECT chapters
- Solution:
  * Modified `build_reflect_chapter_prompt` in `prompt_engineering.py` to format the exploration_goal with the actual question before inserting it into the prompt:
    ```python
    # Format the exploration_goal with the actual question
    formatted_exploration_goal = config["exploration_goal"].format(
        question=previous_lesson.question["question"]
    )
    ```
  * Updated the REFLECT_CHAPTER_PROMPT.format() call to use the formatted_exploration_goal instead of the raw config["exploration_goal"]
- Result:
  * REFLECT chapters now properly include the actual question in the exploration_goal
  * The LLM receives the correct guidance to help the character discover the correct understanding of the specific question
  * Fixed the issue where "the correct understanding of {question}" wasn't loading correctly in the REFLECT chapter prompt

### Question Difficulty Default Setting (2025-03-08)
- Problem: "Very Challenging" questions were being selected instead of defaulting to "Reasonably Challenging" as expected
- Solution:
  * Modified the `sample_question()` function in `app/init_data.py` to set the default difficulty parameter to "Reasonably Challenging"
  * Updated the docstring to reflect this default value
  * Kept the existing logic that falls back to all difficulties if fewer than 3 questions are available for the specified difficulty
  * Added a note about a future UI toggle that will allow users to select difficulty level
- Result:
  * Questions now default to "Reasonably Challenging" when no difficulty is explicitly provided
  * Maintains flexibility for a future UI toggle to override this default
  * Ensures consistent behavior regardless of how the function is called
- Future Enhancement:
  * A UI toggle will be implemented to allow users to select between "Reasonably Challenging" and "Very Challenging" difficulty levels
  * The WebSocket router and adventure state manager already support passing a difficulty parameter
  * The UI implementation will involve adding a toggle in the lesson selection screen

### Lesson Data Refactoring (2025-03-08)
- Problem: Lesson data was stored in a single CSV file (`app/data/lessons.csv`), making it difficult to maintain and update
- Solution:
  * Created a new `LessonLoader` class in `app/data/lesson_loader.py` that:
    - Loads lessons from individual CSV files in the `app/data/lessons/` directory
    - Handles various file encodings and formats
    - Standardizes the difficulty levels to "Reasonably Challenging" and "Very Challenging"
    - Provides methods to filter lessons by topic and difficulty
  * Updated the `sample_question` function in `app/init_data.py` to use the new `LessonLoader` class and support filtering by difficulty
  * Updated the `init_lesson_topics` function in `app/init_data.py` to handle both old and new formats
  * Updated `tests/simulations/story_simulation.py` to use the new `LessonLoader` class
  * Removed the old `app/data/lessons.csv` file as it's no longer needed
- Result:
  * More maintainable lesson data structure with individual files per topic
  * Support for filtering lessons by difficulty level
  * Improved error handling and logging
  * Completed the transition to the new data structure

### Mobile Paragraph Interaction Enhancement (2025-03-07)
- Problem: On mobile, the indigo accent line for paragraphs only worked after the entire chapter finished streaming, and clicking multiple paragraphs would highlight all of them simultaneously
- Solution:
  * Modified the CSS in `theme.css` to support an "active" class alongside the hover state:
    - Added cursor pointer to indicate interactivity
    - Added `.active` class selector to apply the same styling as `:hover`
  * Implemented JavaScript functionality in `index.html`:
    - Created a Set to track which paragraphs are active
    - Added a function `addParagraphListeners()` to add click event listeners to paragraphs
    - Modified the `appendStoryText()` function to call this function after rendering content
    - Ensured only one paragraph can be active at a time by clearing all active states before setting a new one
    - Added state management to reset active paragraphs when starting a new chapter or resetting the application
  * Preserved the active state during text streaming:
    - Restored the active state to paragraphs after content re-rendering
    - Maintained the active state in the Set to persist through updates
- Result:
  * Paragraphs can now be tapped to highlight them with the indigo accent line during text streaming
  * Only one paragraph can be highlighted at a time, with previous highlights being removed
  * The feature works consistently throughout the text streaming process
  * Improved mobile user experience with immediate visual feedback

### CSS File Consolidation (2025-03-07)
- Problem: Too many separate CSS files were causing maintenance challenges and potential conflicts
- Solution:
  * Merged `modern-accents.css` into `theme.css` to consolidate theme-related styles
  * Removed the reference to `modern-accents.css` from `index.html`
  * Maintained clear organization within the combined file:
    - Original theme styles at the top
    - Modern accent enhancements in a clearly commented section
  * Ensured all CSS variables and selectors work harmoniously
- Result:
  * Reduced the number of CSS files from 6 to 5
  * Improved maintainability with related styles in one file
  * Better organization of theme-related styling
  * No change in functionality or appearance for end users

### Modern UI Enhancements (2025-03-07)
- Problem: The UI was functional but felt too minimalist and lacked visual interest, especially when scrolling through text content
- Solution:
  * Implemented subtle UI enhancements with modern styling techniques:
    - Added subtle background patterns and textures
    - Enhanced depth with layered shadows and refined borders
    - Implemented micro-interactions and hover effects
    - Created subtle gradients for buttons and cards
    - Added shine effects and transitions for interactive elements
  * Expanded the color system in `typography.css`:
    - Added new CSS variables for backgrounds, cards, and overlays
    - Created gradient variables for consistent styling
    - Added accent color variations for visual hierarchy
    - Implemented transparent overlays with backdrop filters
  * Enhanced specific UI elements:
    - Improved story container with layered shadows and refined borders
    - Added subtle hover animations to choice cards
    - Enhanced buttons with gradients and shine effects
    - Added a decorative underline to the main heading
    - Improved mobile paragraph styling with hover effects
  * Maintained minimalist aesthetic while adding visual interest:
    - Used very subtle patterns and textures
    - Kept the existing color scheme but added depth
    - Focused on micro-interactions rather than flashy animations
    - Ensured all enhancements work across device sizes
- Result:
  * More engaging and modern UI while maintaining minimalism
  * Enhanced visual hierarchy and depth without overwhelming content
  * Improved interactive feedback for better user experience
  * Consistent styling across all device sizes
  * Better visual interest when scrolling through text content

### Desktop & Mobile UI Alignment (2025-03-07)
- Problem: The user interface on desktop and mobile looked inconsistent, with mobile having a more modern design
- Solution:
  * Applied the mobile UI enhancements to desktop view:
    - Added the indigo accented line with curved-down edges to all screen sizes
    - Applied the left border accent to choice cards on all screen sizes
    - Made the header controls consistent across devices
    - Applied a subtle gradient background to the entire app
  * Implemented specific improvements:
    - Moved the story container styling outside the mobile media query
    - Added hover effects for desktop choice cards
    - Made the header controls border-bottom consistent across all devices
    - Used semi-transparent backgrounds with backdrop blur for a modern look
    - Ensured consistent typography and spacing across devices
  * Cleaned up duplicate styles and organized the CSS files:
    - Removed redundant styles in mobile media queries
    - Created a dedicated narrative-font class for consistent text styling
    - Improved code organization with better comments
- Result:
  * Consistent brand experience across all devices
  * More modern and cohesive visual design
  * Improved readability with consistent styling
  * Better maintainability with organized CSS
  * Enhanced visual hierarchy with consistent accent colors
