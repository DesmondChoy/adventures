# Active Context

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

### CSS Files Reorganization (2025-03-06)
- Problem: There were too many standalone CSS files, making it difficult to maintain and understand the styling structure
- Solution:
  * Merged multiple CSS files into a more organized structure:
    - Consolidated `header-controls.css`, `font-controls.css`, `loader.css`, and `choice-cards.css` into `components.css`
    - Renamed `carousel.css` to `carousel-component.css` to better reflect its purpose
    - Kept `layout.css`, `theme.css`, and `typography.css` as separate files for their specific purposes
  * Updated the HTML file to reference the new CSS structure:
    - Removed references to the merged files
    - Added reference to the renamed carousel component file
  * Organized CSS files by their purpose:
    - `components.css` - Reusable UI components (toast notifications, buttons, loaders, choice cards, etc.)
    - `carousel-component.css` - Specialized carousel component styles
    - `layout.css` - Structural elements, containers, and screen transitions
    - `theme.css` - Color schemes and theme variables
    - `typography.css` - Text styling and formatting
- Result:
  * More maintainable CSS structure with clear separation of concerns
  * Reduced number of CSS files from 9 to 5
  * Better organization of styles by their purpose
  * Improved developer experience with easier-to-find styles
  * No change in functionality or appearance for end users

### CSS Modularization and Transition Improvements (2025-03-06)
- Problem: CSS was scattered throughout the HTML file with inline styles and lacked organization
- Solution:
  * Created two new CSS files:
    - `app/static/css/layout.css` - Contains structural elements, containers, and screen transitions
    - `app/static/css/components.css` - Contains reusable UI components like toasts, buttons, and animations
  * Removed inline styles and replaced them with proper CSS classes:
    - Moved debug info styles to the components.css file
    - Added screen transition classes to all screen containers
    - Created a toast notification component for error messages
    - Added fade-in animation classes for images
  * Enhanced screen transitions:
    - Added proper transition effects between screens
    - Improved the navigation functions to handle transitions correctly
    - Added comments to clarify the transition logic
  * Improved code maintainability:
    - Organized CSS into logical modules
    - Added descriptive comments to explain the purpose of each section
    - Used consistent naming conventions for classes
- Result:
  * More maintainable codebase with better organized CSS
  * Smoother screen transitions throughout the application
  * Improved user experience with consistent animations
  * Reduced code duplication and better separation of concerns

### Carousel Component Refactoring (2025-03-06)
- Problem: The carousel functionality in `index.html` was complex and difficult to maintain with over 1,200 lines of code
- Solution:
  * Created a reusable `Carousel` class in a new `app/static/js/carousel-manager.js` file
  * Encapsulated all carousel-related functionality including rotation, selection, and event handling
  * Updated HTML to use the new class for both category and lesson carousels
  * Removed redundant carousel functions and global variables from the main JavaScript code
  * Implemented proper keyboard navigation through the new class
- Result:
  * Improved code organization with carousel functionality isolated in its own module
  * Reduced duplication by using the same class for both carousels
  * Enhanced maintainability with changes to carousel behavior only needed in one place
  * Better encapsulation with carousel state managed within the class rather than using global variables

### Fixed Loading Spinner Visibility for Chapter 1 (2025-03-05)
- Problem: The loading spinner was disappearing too quickly for Chapter 1 but working fine for other chapters
- Root Cause:
  * The loader was being hidden immediately after content streaming but before image generation tasks for Chapter 1 were complete
  * CSS issues with the loader overlay were causing visibility problems
  * The WebSocket connection handler was hiding the loader too early in the process
- Solution:
  * Modified `stream_and_send_chapter()` in `websocket_service.py` to only hide the loader after all image tasks are complete
  * Updated the WebSocket connection handler in `index.html` to not hide the loader immediately after connection
  * Enhanced the `showLoader()` and `hideLoader()` functions with better error handling and logging
  * Fixed CSS issues in `loader.css` to ensure proper visibility of the loader overlay
  * Added `!important` to the hidden class to prevent style conflicts
- Result: The loading spinner now remains visible during the entire image generation process for Chapter 1, providing a better user experience by accurately reflecting the loading state

### Fixed Subprocess Python Interpreter Issue in Simulation Tests (2025-03-05)
- Problem: The `run_simulation_tests.py` script was failing to run the story simulation properly with a `ModuleNotFoundError: No module named 'websockets'` error, even though the package was installed in the virtual environment
- Root Cause: When the script used commands like `["python", "tests/simulations/story_simulation.py"]` to create subprocesses, it wasn't necessarily using the same Python interpreter that was running the main script
- Solution:
  * Modified `run_simulation_tests.py` to use `sys.executable` instead of "python" when creating subprocess commands
  * Changed the command for getting the run ID from `["python", "tests/simulations/story_simulation.py", "--output-run-id"]` to `[sys.executable, "tests/simulations/story_simulation.py", "--output-run-id"]`
  * Changed the command for running the actual simulation from `["python", "tests/simulations/story_simulation.py"]` to `[sys.executable, "tests/simulations/story_simulation.py"]`
  * This ensures that the subprocess uses the same Python interpreter that's running the main script, which has access to all the installed packages in the virtual environment
- Result: The story simulation now runs correctly when executed through `run_simulation_tests.py`, properly generating chapters and allowing making choices

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
