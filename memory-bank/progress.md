# Progress Log

## 2025-03-03: Image Generation Visual Details Fix

### Fixed Missing Visual Details in Agency Choice Images
- Problem: Visual details in square brackets were not being included in image generation prompts for agency choices
- Root Cause:
  * `categories` dictionary in `prompt_templates.py` wasn't directly accessible
  * Agency name extraction in `image_generation_service.py` wasn't properly handling the "As a..." format
  * Matching logic in `websocket_service.py` wasn't effectively finding the correct agency option with visual details
- Solution:
  * Exposed `categories` dictionary at the module level in `prompt_templates.py`
  * Enhanced `enhance_prompt()` to extract agency names from "As a..." choice texts
  * Added fallback mechanism to look up visual details directly from the `categories` dictionary
  * Implemented multi-stage matching approach in `websocket_service.py` for more accurate agency option identification
- Result: Image generation prompts now correctly include visual details in square brackets, producing more accurate and consistent images for agency choices

## 2025-03-02: Image Generation Gender Consistency

### Fixed Character Gender Inconsistency in Image Generation
- Problem: Image model was generating male characters for agency roles (e.g., Craftsperson) despite female protagonist in narrative
- Solution:
  * Modified `enhance_prompt()` in `image_generation_service.py` to accept and incorporate choice text from narrative
  * Updated `stream_and_send_chapter()` in `websocket_service.py` to pass choice text to image generation
  * Directly included narrative text with gender indicators (e.g., "Elara", "herself") in image prompts
- Result: Generated images maintain gender consistency with narrative, properly depicting female protagonist

## 2025-03-02: Prompt Template Optimizations

### Fixed Duplicate Plot Twist Guidance
- Problem: Plot twist guidance was being duplicated in Chapter 2 prompts
- Solution:
  * Modified `_get_phase_guidance()` to return only base phase guidance without plot twist guidance
  * Maintained separate plot twist guidance in `build_story_chapter_prompt()` with the `{plot_twist_guidance}` placeholder
  * Updated docstring to clarify the function's more specific purpose
- Result: Eliminated duplicate "Plot Twist Development" sections in story chapter prompts

### Removed Duplicate Phase Guidance
- Problem: Phase guidance was duplicated in prompts (prepended in `build_user_prompt()` and extracted in chapter builders)
- Solution:
  * Removed "Exposition Focus" line from all templates in `prompt_templates.py`
  * Removed exposition focus extraction in all chapter building functions
  * Modified template `.format()` calls to remove the parameter
- Result: Reduced token usage and improved maintainability

### Reintegrated Phase Guidance Function
- Problem: `_get_phase_guidance()` was defined but unused
- Solution:
  * Modified `build_user_prompt()` to get phase guidance and prepend to all prompts
  * Maintained original chapter-specific functions
  * Centralized phase guidance logic
- Result: Consistent phase guidance across all chapter types

## 2025-03-01: Image Generation and Prompt Improvements

### Enhanced Image Generation Reliability
- Problem: Image generation failing with "NoneType has no len()" error
- Solution:
  * Increased retries from 2 to 5 in `generate_image_async()` and `_generate_image()`
  * Added robust null checking for API responses
  * Implemented graceful fallbacks for failed generation
- Result: More reliable image generation with better error handling

### Standardized Image Generation Configuration
- Problem: Inconsistent configuration between services
- Solution:
  * Changed environment variable from `GEMINI_API_KEY` to `GOOGLE_API_KEY`
  * Updated API initialization to use `genai.configure()`
  * Enhanced debug logging similar to GeminiService
- Result: Consistent configuration across services

### Fixed Image Generation API Compatibility
- Problem: Incompatibility with Google Generative AI SDK
- Solution:
  * Updated imports to use correct SDK
  * Modified client initialization and method calls
  * Updated response handling for new API structure
- Result: Working image generation for Chapter 1 agency choices

### Streamlined LLM Prompts for All Chapters
- Problem: Inconsistent prompt styles across chapters
- Solution:
  * Extended streamlined approach to all chapter types
  * Created unified `build_prompt()` function
  * Removed redundant files and conditional checks
  * Consolidated templates and engineering functions
- Result: Consistent, maintainable prompts with reduced token usage

## 2025-02-28: Agency Implementation and Narrative Improvements

### Fixed F-String Syntax Error
- Problem: Trailing space in f-string causing syntax error
- Solution: Removed trailing space in agency guidance section
- Result: Fixed application startup issue

### Agency Implementation
- Problem: Lack of meaningful user agency throughout adventure
- Solution:
  * Added four agency categories in first chapter (items, companions, roles, abilities)
  * Implemented agency detection and storage in `websocket_service.py`
  * Added reference tracking in `adventure_state_manager.py`
  * Created evolution system in REFLECT chapters
- Result: Meaningful agency that evolves throughout the adventure

### REFLECT Chapter Narrative Integration
- Problem: REFLECT chapters felt like detached tests
- Solution:
  * Created unified narrative approach for correct/incorrect answers
  * Removed "correct/incorrect" structure from choices
  * Made all choices story-driven without educational labels
  * Used Socratic method for deeper understanding
- Result: More natural integration of educational content

### Removed Obsolete Code
- Problem: Unused `CHOICE_FORMAT_INSTRUCTIONS` constant
- Solution: Removed constant and its import
- Result: Improved code maintainability

### UI Improvements
- Problem: "Swipe to explore" tip showing on desktop
- Solution: Added media query to hide on screens > 768px
- Result: Device-appropriate UI hints

### Story Object Method for Lessons
- Problem: Disconnect between narrative and educational content
- Solution:
  * Implemented Story Object Method for intuitive narrative bridges
  * Required exact question to appear verbatim in narrative
  * Allowed more natural placement of questions
- Result: Better integration of educational content

## 2025-02-27: Prompt Engineering Enhancements

### Phase-Specific Choice Instructions
- Problem: Generic choice instructions across all story phases
- Solution:
  * Created `BASE_CHOICE_FORMAT` with common instructions
  * Added phase-specific guidance dictionary
  * Implemented `get_choice_instructions(phase)` function
- Result: More contextually appropriate choices for each phase

### Markdown Structure for Prompts
- Problem: Poor organization in LLM prompts
- Solution:
  * Implemented markdown-based structure
  * Created clear visual hierarchy
  * Enhanced formatting for lesson content
- Result: Better organized, more effective prompts

### Enhanced REFLECT Chapter Implementation
- Problem: Limited variety in REFLECT challenges
- Solution:
  * Added multiple challenge types for correct answers
  * Restructured incorrect answer handling
  * Added challenge type tracking in metadata
- Result: More varied and engaging REFLECT chapters
