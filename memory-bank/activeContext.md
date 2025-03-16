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

## Improved Learning Report Display in Simulation Log Summary (2025-03-16)

1. **Enhanced Learning Report Display in Simulation Log Summary Viewer:**
   * Problem: The learning report in `show_summary_from_log.py` was showing redundant information for correctly answered questions
   * Solution:
     - Modified the learning report generation in `show_summary_from_log.py` to:
       * Always show "Your Answer" with a "(Correct)" or "(Incorrect)" indicator
       * Only show "Correct Answer" when the user's answer was incorrect
       * Always show the explanation regardless of correctness
     - Added code to handle cases where the Learning Report section isn't found in the summary content
     - Ensured the thank you message is preserved at the end of the report
   * Result:
     - More streamlined learning report that avoids redundancy
     - For correct answers: Shows only "Your Answer: [answer] (Correct)" followed by the explanation
     - For incorrect answers: Shows both "Your Answer: [answer] (Incorrect)" and "Correct Answer: [correct_answer]" followed by the explanation
     - Clearer educational feedback for users
     - Consistent display of explanations for all questions

## Separated Image Scene Generation from Chapter Summaries (2025-03-15)

1. **Implemented Dedicated Image Scene Generation:**
   * Problem: The application was using chapter summaries for both narrative recaps and image generation, creating a compromise between two different needs
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
   * Result:
     - Chapter summaries now focus on comprehensive narrative overviews (better for SUMMARY chapter)
     - Image generation now focuses on the most visually compelling moments (better for illustrations)
     - More dynamic, exciting illustrations that capture specific dramatic moments
     - Clearer separation of concerns between the two different needs

## Removed Chapter Summary Truncation for Complete Summaries (2025-03-15)

1. **Removed Chapter Summary Truncation:**
   * Problem: Chapter summaries were being artificially truncated to 40 words when they exceeded 50 words, causing incomplete summaries ending with "..."
   * Solution:
     - Removed the truncation logic from the `generate_chapter_summary` method
     - Maintained the LLM prompt that still guides it to generate concise summaries
     - Kept the empty summary check and fallback mechanism
   * Result:
     - Chapter summaries are now displayed in full as generated by the LLM
     - No more truncated summaries ending with "..."
     - More complete and informative chapter summaries throughout the application
     - Better context in the summary chapter where these summaries are displayed

## Fixed Simulation Log Summary Extraction for Complete Chapter Summaries (2025-03-15)

1. **Fixed Chapter Summary Extraction from Simulation Logs:**
   * Problem: The `show_summary_from_log.py` script wasn't extracting all chapter summaries from simulation logs, resulting in dummy summaries for chapters 9-10
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
   * Result:
     - The script now correctly extracts all chapter summaries from simulation logs
     - No more dummy summaries for chapters 9-10
     - Complete summary chapter with all 10 chapters and educational questions
     - Better understanding of the story simulation structure for future development

## Improved Chapter Summaries with Narrative Focus (2025-03-14)

1. **Enhanced Chapter Summary Generation:**
   * Problem: Chapter summaries were optimized for image generation (visual scenes) rather than narrative progression, making the SUMMARY chapter less cohesive and educational
   * Solution:
     - **Created New Prompt Template:**
       * Added `SUMMARY_CHAPTER_PROMPT` to `app/services/llm/prompt_templates.py`
       * Designed the prompt to focus on narrative events, character development, and educational content
       * Increased word count guidance to 30-40 words for more comprehensive summaries
     - **Updated Image Generation Service:**
       * Imported the new prompt template in `app/services/image_generation_service.py`
       * Replaced the hardcoded visual-focused prompt with the narrative-focused template
       * Maintained the same LLM service call structure for compatibility
   * Result:
     - Chapter summaries now capture key story events and character development
     - Summaries include important choices and educational content when present
     - Consistent third-person, past tense voice throughout all summaries
     - The SUMMARY chapter provides a more cohesive and educational recap of the adventure

## Enhanced Simulation Log Summary Viewer with Educational Questions (2025-03-14)

1. **Enhanced Simulation Log Summary Viewer:**
   * Problem: The `show_summary_from_log.py` script was not extracting chapter summaries from simulation logs and was showing dummy summaries instead. Additionally, educational questions encountered during the adventure were not being displayed in the Learning Report section.
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
   * Result:
     - The script now correctly extracts chapter summaries from simulation logs
     - Educational questions are displayed in the Learning Report section
     - The summary provides a complete overview of the adventure, including both narrative and educational content

2. **Fixed SUMMARY Chapter Functionality:**
   * Problem: After clicking the "Reveal Your Adventure Summary" button at the end of a 10-chapter adventure, the application showed a loading spinner but never actually loaded the summary page.
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
   * Benefits:
     - Enables testing of the SUMMARY chapter functionality without manually going through all 10 chapters
     - Provides structured data for automated testing of the chapter summaries feature
     - Captures chapter summaries in a format that can be easily extracted and analyzed
     - Maintains alignment with how chapter summaries are implemented in the actual application

## Enhanced Summary Implementation with Progressive Chapter Summaries (2025-03-11)

1. **Enhanced Summary Implementation:**
   * Purpose: Improve the SUMMARY chapter by generating and storing chapter summaries throughout the adventure
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
   
   * Design Principles Applied:
     - Maintained consistent visual theming with the existing app
     - Created a more detailed chronological recap of the adventure journey
     - Preserved chapter context by showing chapter numbers and types
     - Maintained the same learning report format for educational value
     - Improved reliability through distributed processing

## Fixed Paragraph Formatter Using Incomplete Text (2025-03-10)

1. **Fixed Paragraph Formatter Bug:**
   * Problem: Paragraph formatter was detecting text without proper paragraph formatting, but only reformatting the initial buffer (first ~1000 characters) instead of the full response
   * Solution:
     - Modified all instances in both OpenAIService and GeminiService to use `full_response` instead of `collected_text` when reformatting is needed
     - Updated the code in OpenAIService.generate_with_prompt, OpenAIService.generate_chapter_stream, GeminiService.generate_with_prompt, and GeminiService.generate_chapter_stream
     - Maintained the existing retry mechanism (up to 3 attempts with progressively stronger formatting instructions)
   * Result:
     - Complete LLM responses now have proper paragraph formatting throughout the entire text
     - Improved readability for users, especially for longer responses
     - Maintained the streaming experience when formatting isn't needed
     - Fixed the issue where debug logs showed detection and reformatting but the output still lacked proper formatting

## Fixed Chapter Summary Generation for Image Prompts (2025-03-10)

1. **Fixed Chapter Summary Generation for Image Prompts:**
   * Problem: Chapter summaries generated by the LLM weren't being included in image generation prompts
   * Solution:
     - Implemented service-specific handling for different LLM providers:
       - For Gemini: Used direct API call instead of streaming for summary generation
       - For OpenAI: Maintained the streaming approach which works correctly
     - Added comprehensive logging to track the raw response, its length, and processed summary
     - Enhanced empty check to consider very short summaries (less than 5 characters) as empty
     - Improved fallback mechanism to use the first paragraph of chapter content when needed
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

## Implemented Paragraph Formatting for LLM Responses (2025-03-09)

1. **Implemented Paragraph Formatting for LLM Responses:**
   * Problem: LLM responses occasionally lacked proper paragraph breaks, causing text to render as one continuous paragraph
   * Solution:
     - Created a new `paragraph_formatter.py` module with functions to detect and fix text without proper paragraph formatting
     - Implemented `needs_paragraphing()` function to detect text that needs formatting based on length, existing paragraph breaks, sentence count, and dialogue markers
     - Added `reformat_text_with_paragraphs()` function that uses the same LLM service to add proper paragraph breaks
     - Implemented multiple retry attempts (up to 3) with progressively stronger formatting instructions
     - Modified both OpenAIService and GeminiService to check for paragraph formatting needs and apply reformatting when necessary
     - Added comprehensive logging of prompts and responses for debugging
   * Result:
     - Ensures all LLM responses have proper paragraph formatting for better readability
     - Maintains streaming experience when formatting isn't needed
     - Provides detailed logging for monitoring and debugging
     - Gracefully handles cases where reformatting fails

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
