# Active Context

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
- Modified `app/services/chapter_manager.
