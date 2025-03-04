# Active Context

## Core Architecture

1. **Adventure Flow (`app/routers/web.py`, `app/services/chapter_manager.py`):**
   * ChapterType enum: LESSON, STORY, REFLECT, CONCLUSION
   * Content sources in `prompt_engineering.py`:
     - LESSON: `lessons.csv` + LLM wrapper
     - STORY: Full LLM generation with choices
     - REFLECT: Narrative-driven follow-up to LESSON
     - CONCLUSION: Resolution without choices

2. **Chapter Sequencing (`chapter_manager.py`):**
   * First chapter: STORY
   * Second-to-last: STORY
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

## Recent Changes

### Mobile Font Size Controls Implementation (2025-03-04)
- Problem: Mobile users needed a way to adjust font size for better readability
- Solution:
  * Created a new `font-size-manager.js` file to handle font size adjustments
  * Added font size controls (plus/minus buttons and percentage display) to the header row
  * Removed the progress bar as it wasn't needed
  * Styled controls using the app's indigo theme colors
  * Implemented show/hide behavior on scroll (matching chapter indicator behavior)
  * Made controls only visible on mobile devices (screen width ≤ 768px)
  * Ensured font size defaults to 100% for new users
  * Saved user preferences to localStorage for persistence
- Result: Mobile users can now easily adjust text size for better readability while maintaining the app's visual design

### Debug Toggle Removal (2025-03-04)
- Problem: Debug toggle button was visible to users on both desktop and mobile
- Solution:
  * Removed the "Toggle Debug Info" button from the UI
  * Kept the debug info div in the HTML but hidden by default
  * Added a comment explaining how developers can still access it via the console
- Result: Cleaner user interface without developer tools visible to end users

### Optimized Image Generation Prompts (2025-03-04)
- Problem: Image generation prompts were bloated with redundant information, causing inconsistent results
- Solution:
  * Restructured prompt format to focus on essential elements: `Fantasy illustration of [Agency Name] in [Story Name], [Visual Details], with [adventure_state.selected_sensory_details["visuals"]], [Base Style]`
  * Rewrote `enhance_prompt()` in `image_generation_service.py` to extract the complete agency name with visual details up to the closing bracket
  * Added a helper method `_lookup_visual_details()` to find visual details when not present in the original prompt
  * Simplified agency option extraction in `websocket_service.py` to be more direct and reliable
- Result: More consistent image generation with reduced token usage and improved visual quality by focusing on essential elements

### Fixed Outdated References to new_stories.yaml (2025-03-04)
- Problem: After refactoring story data into individual files, some parts of the codebase were still referencing the old `new_stories.yaml` file, causing errors
- Solution:
  * Updated `app/routers/web.py` to use the new `StoryLoader` class instead of directly loading from the old YAML file
  * Updated `app/services/websocket_service.py` to use the `StoryLoader` class in the `generate_chapter()` function
  * Updated `app/init_data.py` to use the `StoryLoader` class in the `load_story_data()` function
  * Updated `tests/simulations/story_simulation.py` to use the `StoryLoader` class in the `load_story_data()` function
- Result: Fixed "Failed to load story data" and "Error generating chapter: [Errno 2] No such file or directory: 'app/data/new_stories.yaml'" errors, ensuring all parts of the application use the new story data structure

### Fixed Character Encoding Issue in Story Loader (2025-03-04)
- Problem: Character encoding error when loading YAML files: `'charmap' codec can't decode byte 0x9d in position 3643: character maps to <undefined>`
- Solution:
  * Modified `load_all_stories()` method in `app/data/story_loader.py` to explicitly use UTF-8 encoding when opening files
  * Changed `with open(file_path, "r") as f:` to `with open(file_path, "r", encoding="utf-8") as f:`
- Result: Fixed character encoding issues when loading story files, ensuring proper handling of special characters in YAML content

### Story Data Organization Refactoring (2025-03-04)
- Problem: All story categories were in a single YAML file, making maintenance difficult and increasing risk of syntax errors
- Solution:
  * Created a dedicated `app/data/stories/` directory to store individual story files
  * Split the monolithic `new_stories.yaml` into individual files for each story category
  * Implemented a dedicated `StoryLoader` class in `app/data/story_loader.py`
  * Updated `chapter_manager.py` to use the new loader
  * Created proper test files in `tests/data/` directory
- Result: Improved maintainability, reduced risk of syntax errors, better scalability for adding new stories, and enhanced collaboration potential

### Dynamic Adventure Topic Reference in Exposition Phase (2025-03-04)
- Problem: World building guidance in Exposition phase was generic and didn't reference the specific adventure topic selected by the user
- Solution:
  * Modified the BASE_PHASE_GUIDANCE dictionary in `prompt_templates.py` to add an {adventure_topic} placeholder in the "World Building" section of the "Exposition" phase guidance
  * Updated the `_get_phase_guidance()` function in `prompt_engineering.py` to replace the placeholder with the actual adventure topic name from `state.metadata["non_random_elements"]["name"]`
- Result: Exposition phase guidance now dynamically references the specific adventure topic (e.g., "Jade Mountain") selected by the user, creating a more tailored and immersive storytelling experience

### Renamed `setting_types` to `settings` and Removed `story_rules` (2025-03-03)
- Problem: Needed to simplify the data model and update field naming for clarity
- Solution:
  * Renamed `setting_types` to `settings` in all story categories in `app/data/new_stories.yaml`
  * Removed all `story_rules` sections from each story category in `app/data/new_stories.yaml`
  * Updated the validator in `app/models/story.py` to use `settings` instead of `setting_types` and removed `story_rules` from required categories
  * Modified `app/services/chapter_manager.py` to update the required categories and selection logic
  * Updated references in `app/services/llm/prompt_engineering.py` to use `settings` instead of `setting_types` and removed references to `story_rules`
  * Updated the `SYSTEM_PROMPT_TEMPLATE` in `app/services/llm/prompt_templates.py` to use `settings` and removed the `story_rules` line
  * Updated `app/services/image_generation_service.py` to use `settings` instead of `setting_types`
- Result: Simplified data model while maintaining core functionality; system now uses `settings` instead of `setting_types` and no longer requires or uses `story_rules` in narrative generation

### Removed Unused `character_archetypes` Field (2025-03-03)
- Removed the unused `character_archetypes` field from story categories
- Updated `app/data/new_stories.yaml` to remove the `character_archetypes` sections from each story category
- Modified `app/models/story.py` to remove `character_archetypes` from the required categories in validation
- Updated `app/services/chapter_manager.py` to remove `character_archetypes` from the required categories
- Removed `character_archetypes` from the system prompt template in `app/services/llm/prompt_templates.py`
- Removed the `character_archetypes` parameter from the system prompt formatting in `app/services/llm/prompt_engineering.py`

### Removed Unused `tone` Field (2025-03-03)
- Removed the unused `tone` field from story categories as it wasn't being passed to LLM prompts
- Updated `app/data/new_stories.yaml` to remove the `tone` field from each story category
- Modified `app/services/chapter_manager.py` to remove `tone` from the `non_random_elements` dictionary
- Updated `app/database.py` to remove the `tone` Column from the `StoryCategory` class
- Changed `app/init_data.py` to remove the `tone` field when creating the `db_category` object
- Recreated the database to apply the schema changes

### LLM Response Formatting Improvement (2025-03-03)
- Fixed issue with LLM responses sometimes beginning with "chapter" despite system prompt instructions
- Updated regex pattern in `websocket_service.py` to catch and remove both numbered and unnumbered chapter prefixes
- Changed pattern from `r"^Chapter\s+\d+:\s*"` to `r"^Chapter(?:\s+\d+)?:?\s*"`
- Applied fix in three key locations in the processing pipeline to ensure consistent formatting

### Image Generation Visual Details Fix (2025-03-03)
- Fixed issue with visual details not being included in image generation prompts for agency choices
- Exposed `categories` dictionary in `prompt_templates.py` for direct access by other modules
- Enhanced `enhance_prompt()` in `image_generation_service.py` to better extract agency names from choice text
- Added fallback mechanism to look up visual details directly from the `categories` dictionary
- Improved matching logic in `websocket_service.py` to find the correct agency option with visual details
- Implemented multi-stage matching approach for more accurate agency option identification

### Image Generation Gender Consistency (2025-03-02)
- Modified `enhance_prompt()` in `image_generation_service.py` to accept choice text parameter
- Updated `stream_and_send_chapter()` in `websocket_service.py` to pass choice text to image generation
- Incorporated narrative text with gender indicators directly into image prompts
- Improved consistency between narrative protagonist (female) and generated images

### Streamlined Prompts for All Chapters (2025-03-01)
- Extended streamlined approach to all chapter types in `prompt_templates.py` and `prompt_engineering.py`
- Created unified `build_prompt()` function for all chapter types
- Removed redundant files and conditional checks in `providers.py`
- Reduced token usage while preserving essential guidance

### Enhanced Image Generation (2025-03-01)
- Increased retries from 2 to 5 in `generate_image_async()` and `_generate_image()`
- Added robust null checking to prevent "NoneType has no len()" errors
- Standardized to use `GOOGLE_API_KEY` environment variable
- Implemented graceful fallbacks for failed image generation

### Agency Implementation (2025-02-28)
- First chapter agency choice from four categories stored in `state.metadata["agency"]`
- Agency evolution in REFLECT chapters based on correct/incorrect answers
- Agency tracking in `update_agency_references()` in `adventure_state_manager.py`
- Agency guidance templates in `prompt_templates.py`

### Narrative Improvements (2025-02-28)
- Story Object Method in `build_lesson_chapter_prompt()` for intuitive narrative bridges
- Unified REFLECT chapter approach in `build_reflect_chapter_prompt()`
- Phase-specific choice instructions via `get_choice_instructions(phase)`
- Markdown-based prompt structure for better organization

## Testing Framework

- **Simulation (`tests/simulations/story_simulation.py`):**
  * Generates structured log data with standardized prefixes
  * Verifies complete workflow execution
  * Validates component integration

- **Test Files:**
  * `tests/simulations/test_simulation_functionality.py`: Verifies chapter sequences, ratios, state transitions
  * `tests/simulations/test_simulation_errors.py`: Tests error handling, recovery, logging configuration
  * `tests/simulations/run_simulation_tests.py`: Orchestrates server, simulation, and test execution
  * `tests/data/test_story_loader.py`: Tests story data loading functionality
  * `tests/data/test_story_elements.py`: Tests random element selection
  * `tests/data/test_chapter_manager.py`: Tests adventure state initialization
