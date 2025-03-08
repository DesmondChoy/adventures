# Progress Log

## 2025-03-08: Enhanced CORRECT_ANSWER_CONSEQUENCES and INCORRECT_ANSWER_CONSEQUENCES Templates

### Improved Learning Impact with Explanation Integration
- Problem: The CORRECT_ANSWER_CONSEQUENCES and INCORRECT_ANSWER_CONSEQUENCES templates weren't using the explanation column from lesson data
- Root Cause:
  * The explanation field was loaded from CSV files and stored in the question data
  * However, it wasn't being included in the templates for learning impact
  * This meant valuable educational content wasn't being shown in the story when a student answered a question
- Solution:
  * Modified the templates in `prompt_templates.py` to include the explanation:
    ```python
    CORRECT_ANSWER_CONSEQUENCES = """## Learning Impact
    - Show how understanding {question} connects to their current situation
    - Build confidence from this success that carries into future challenges: "{explanation}"
    - Integrate this knowledge naturally into the character's approach"""

    INCORRECT_ANSWER_CONSEQUENCES = """## Learning Impact
    - Acknowledge the misunderstanding about {question}
    - Create a valuable learning moment from this correction: "{explanation}"
    - Show how this new understanding affects their approach to challenges"""
    ```
  * Updated the `process_consequences` function in `prompt_engineering.py` to extract and pass the explanation:
    ```python
    # Get the explanation from the lesson question, or use a default if not available
    explanation = lesson_question.get("explanation", "")
    
    if is_correct:
        return CORRECT_ANSWER_CONSEQUENCES.format(
            correct_answer=correct_answer,
            question=lesson_question["question"],
            explanation=explanation,
        )
    else:
        return INCORRECT_ANSWER_CONSEQUENCES.format(
            chosen_answer=chosen_answer,
            correct_answer=correct_answer,
            question=lesson_question["question"],
            explanation=explanation,
        )
    ```
- Result:
  * When a student answers a question incorrectly, the prompt now includes the specific explanation from the lesson data
  * For example, if a student incorrectly answers a question about the 1964 Singapore riots, the prompt will include the detailed explanation about ethnic tensions and political conflicts
  * This provides more context for the learning moment and helps the LLM create more educational content
  * The implementation is minimal and focused, affecting only the consequences templates
  * Gracefully handles cases where explanations might be missing by using an empty string as default

## 2025-03-08: Fixed Question Difficulty Default in WebSocket Service

### Fixed Question Difficulty Default in WebSocket Service
- Problem: "Very Challenging" questions were still being selected for Chapter 2 despite the fix to default to "Reasonably Challenging" in the `sample_question()` function
- Root Cause:
  * While the `sample_question()` function in `app/init_data.py` was correctly updated to default to "Reasonably Challenging"
  * In `websocket_service.py`, the difficulty was being retrieved from state metadata with a default of `None`:
    ```python
    # Get difficulty from state metadata if available (for future difficulty toggle)
    difficulty = state.metadata.get("difficulty", None)
    ```
  * This `None` value was then passed to `sample_question()`, which overrode the default parameter value
  * Even though `sample_question()` had a default parameter of "Reasonably Challenging", it was never used because `None` was explicitly passed
- Solution:
  * Modified the code in `websocket_service.py` to use "Reasonably Challenging" as the default when retrieving from state metadata:
    ```python
    # Get difficulty from state metadata if available (for future difficulty toggle)
    difficulty = state.metadata.get("difficulty", "Reasonably Challenging")
    ```
  * This ensures that even if no difficulty is set in the state metadata, it will default to "Reasonably Challenging"
- Result:
  * Questions now consistently default to "Reasonably Challenging" when no difficulty is explicitly provided
  * Fixed the specific issue with the question "What does it mean when a farm animal exhibits repetitive behaviors?" in Chapter 2
  * Maintains flexibility for a future UI toggle to override this default
  * Ensures consistent behavior regardless of how the function is called

## 2025-03-08: Fixed Question Placeholder in REFLECT Chapters

### Fixed Missing Question Placeholder Replacement in Reflection Chapters
- Problem: The `{question}` placeholder in the exploration_goal wasn't being properly replaced in REFLECT chapters
- Root Cause:
  * In `prompt_templates.py`, the REFLECT_CONFIG dictionary contains an exploration_goal with a `{question}` placeholder:
    ```python
    "exploration_goal": "discover the correct understanding of {question} through guided reflection"
    ```
  * When this config was used in `prompt_engineering.py` to build the REFLECT chapter prompt, the `{question}` placeholder wasn't being replaced
  * The placeholder was being treated as a literal string, not as a placeholder to be replaced with the actual question
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

## 2025-03-08: Utilized Explanation Column in REFLECT Chapters

### Enhanced Educational Content in Reflection Chapters
- Problem: The `explanation` column in lesson CSV files wasn't being utilized in the prompts
- Root Cause:
  * The explanation field was loaded from CSV files and stored in the question data
  * However, it wasn't being passed to the LLM in any of the prompt templates
  * This meant valuable educational content was being ignored in the story generation
- Solution:
  * Modified `REFLECT_CHAPTER_PROMPT` in `prompt_templates.py` to include a new "Educational Context" section
  * Added an `explanation_guidance` parameter to the template
  * Updated `build_reflect_chapter_prompt` in `prompt_engineering.py` to:
    - Extract the explanation from the question data
    - Create an explanation guidance string that incorporates the explanation
    - Add a fallback message for cases where no explanation is provided
    - Pass the explanation_guidance parameter to the template
- Result:
  * REFLECT chapters now include the explanation from the CSV file
  * The LLM can create more educationally sound reflection chapters
  * Students receive better explanations of concepts, regardless of whether they answered correctly or incorrectly
  * The implementation is minimal and focused, only affecting REFLECT chapters
  * Gracefully handles cases where explanations might be missing

## 2025-03-08: Fixed Question Difficulty Default

### Set Default Difficulty for Question Sampling
- Problem: "Very Challenging" questions were being selected instead of defaulting to "Reasonably Challenging" as expected
- Root Cause:
  * The `sample_question()` function in `app/init_data.py` had no default value for the `difficulty` parameter
  * Without an explicit difficulty setting, the system randomly sampled from all available questions regardless of difficulty
  * A TODO comment indicated this was meant to be controlled by a UI toggle that hasn't been implemented yet
- Solution:
  * Modified the `sample_question()` function to set the default difficulty parameter to "Reasonably Challenging"
  * Updated the docstring to reflect this default value
  * Kept the existing logic that falls back to all difficulties if fewer than 3 questions are available for the specified difficulty
- Result:
  * Questions now default to "Reasonably Challenging" when no difficulty is explicitly provided
  * Maintains flexibility for a future UI toggle to override this default
  * Ensures consistent behavior regardless of how the function is called

## 2025-03-08: Completed Lesson Data Refactoring

### Removed Legacy Lessons CSV File and Updated References
- Problem: The old `app/data/lessons.csv` file was still present and referenced in some parts of the code, despite the refactoring to use individual CSV files
- Root Cause:
  * The refactoring to use individual CSV files in the `app/data/lessons/` directory was incomplete
  * The `tests/simulations/story_simulation.py` file still directly referenced the old CSV file
  * The old CSV file was still present in the repository
- Solution:
  * Updated `tests/simulations/story_simulation.py` to use the `LessonLoader` class instead of directly loading from the old CSV file
  * Removed the old `app/data/lessons.csv` file as it's no longer needed
  * Updated documentation in memory-bank files to reflect the completed transition
- Result:
  * Completed the transition to the new data structure
  * Removed redundant code and files
  * Improved consistency across the codebase
  * Simplified the lesson loading process

## 2025-03-08: Fixed Lesson Loader CSV Format Handling

### Enhanced CSV Parsing and Topic Matching
- Problem: The `LessonLoader` class wasn't correctly parsing the new CSV format with quoted fields, causing errors when filtering by topic
- Root Cause:
  * CSV files were reformatted with proper quotes around each field
  * The custom parsing logic in `LessonLoader` wasn't handling the quoted fields correctly
  * Topic matching was case-sensitive and didn't handle whitespace variations
  * Only 1 lesson was being found for "Human Body" topic when there should be 50
- Solution:
  * Completely rewrote the `load_all_lessons` method to use pandas' built-in CSV parsing with proper quoting parameters
  * Enhanced the `get_lessons_by_topic` method to use case-insensitive matching
  * Added fallback strategies for topic matching:
    - First try exact case-insensitive matching
    - Then try with stripped whitespace
    - Finally try partial matching if needed
  * Updated `get_lessons_by_difficulty` and `get_lessons_by_topic_and_difficulty` to use the same case-insensitive approach
  * Added detailed logging to help diagnose any future issues
  * Removed the fallback to the old CSV file since it's no longer needed
- Result:
  * Successfully loads all 150 lessons from the CSV files in the `app/data/lessons/` directory
  * Correctly finds all 50 lessons for the "Human Body" topic
  * More robust topic and difficulty matching with case-insensitive comparisons
  * Better error handling and logging for easier debugging
  * Fixed the "Need at least 3 questions, but only have 1" error in adventure state initialization

## 2025-03-07: Lesson Data Refactoring

### Improved Lesson Data Management with Individual Files
- Problem: Lesson data was stored in a single CSV file (`app/data/lessons.csv`), making it difficult to maintain and update
- Root Cause:
  * All lesson data was in a single CSV file, making it hard to organize by topic
  * No support for filtering by difficulty level
  * Limited flexibility for adding new lessons or updating existing ones
  * Potential for data corruption when editing a large CSV file
- Solution:
  * Created a new `LessonLoader` class in `app/data/lesson_loader.py` that:
    - Attempts to load lessons from individual CSV files in the `app/data/lessons/` directory
    - Falls back to the old `app/data/lessons.csv` file if needed
    - Handles various file encodings and formats
    - Standardizes the difficulty levels to "Reasonably Challenging" and "Very Challenging"
    - Provides methods to filter lessons by topic and difficulty
  * Updated the `sample_question` function in `app/init_data.py` to use the new `LessonLoader` class and support filtering by difficulty
  * Updated the `init_lesson_topics` function in `app/init_data.py` to handle both old and new formats
  * Ensured backward compatibility with the existing code
- Result:
  * More maintainable lesson data structure with individual files per topic
  * Support for filtering lessons by difficulty level
  * Improved error handling and logging
  * Backward compatibility with the old CSV file
  * Smooth transition path from old to new data structure

## 2025-03-07: CSS File Consolidation

### Improved Frontend Architecture with CSS Consolidation
- Problem: Too many separate CSS files were causing maintenance challenges and potential conflicts
- Root Cause:
  * CSS files were being added for specific features without considering overall organization
  * Modern UI enhancements were in a separate file from other theme-related styles
  * Potential for style conflicts or overrides between files
  * Increased complexity for developers to understand the styling structure
- Solution:
  * Merged `modern-accents.css` into `theme.css` to consolidate theme-related styles:
    - Appended modern accent styles to the end of theme.css
    - Added clear comments to separate the original theme styles from modern accents
    - Ensured all CSS variables and selectors work harmoniously
  * Removed the reference to `modern-accents.css` from `index.html`
  * Maintained organization within the combined file:
    - Original theme styles at the top
    - Modern accent enhancements in a clearly commented section
  * Verified that all styles continue to work as expected
- Result:
  * Reduced the number of CSS files from 6 to 5
  * Improved maintainability with related styles in one file
  * Better organization of theme-related styling
  * No change in functionality or appearance for end users
  * Simplified CSS loading in the HTML file

## 2025-03-07: Modern UI Enhancements

### Enhanced Visual Design with Subtle Modern Touches
- Problem: The UI was functional but felt too minimalist and lacked visual interest, especially when scrolling through text content
- Root Cause:
  * Minimal styling focused on functionality without visual depth
  * Limited use of modern CSS features like gradients, shadows, and animations
  * Lack of visual hierarchy and interactive feedback
  * Plain white backgrounds with limited texture or depth
- Solution:
  * Implemented subtle UI enhancements with modern styling techniques:
    - Added subtle background patterns and textures using SVG backgrounds
    - Enhanced depth with layered shadows and refined borders
    - Implemented micro-interactions and hover effects for better feedback
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

## 2025-03-07: Desktop & Mobile UI Alignment

### Unified UI Experience Across All Devices
- Problem: The user interface on desktop and mobile looked inconsistent, with mobile having a more modern design
- Root Cause:
  * Mobile-specific UI enhancements were not applied to desktop view
  * CSS was organized in a way that kept desktop and mobile styles separate
  * Design elements like the indigo accented line and left border accent were only applied to mobile
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

## 2025-03-06: CSS Files Reorganization

### Improved Frontend Architecture with CSS Organization
- Problem: There were too many standalone CSS files, making it difficult to maintain and understand the styling structure
- Root Cause:
  * CSS files were created ad-hoc as new features were added
  * No clear organization strategy for CSS files
  * Similar styles were spread across multiple files
  * No clear separation of concerns between different types of styles
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

## 2025-03-06: CSS Modularization and Transition Improvements

### Improved Frontend Architecture with CSS Organization and Transitions
- Problem: CSS was scattered throughout the HTML file with inline styles and lacked organization
- Root Cause:
  * Inline styles were used for various UI components
  * No dedicated CSS files for layout and components
  * Screen transitions lacked proper animation effects
  * Error messages used inline styling instead of a reusable component
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

## 2025-03-06: Carousel Component Refactoring

### Improved Frontend Architecture with Reusable Carousel Component
- Problem: The carousel functionality in `index.html` was complex and difficult to maintain with over 1,200 lines of code
- Root Cause:
  * All carousel functionality was embedded directly in the main HTML file
  * Duplicate code for category and lesson carousels
  * Global variables for carousel state management
  * Complex event handling logic mixed with other UI code
- Solution:
  * Created a reusable `Carousel` class in a new `app/static/js/carousel-manager.js` file with:
    - Constructor that accepts configuration options (elementId, itemCount, dataAttribute, inputId, onSelect)
    - Methods for rotation, selection, and event handling
    - Support for keyboard, button, and touch controls
    - Mobile-specific optimizations
  * Updated HTML to use the new class for both category and lesson carousels:
    ```javascript
    // Initialize category carousel
    window.categoryCarousel = new Carousel({
        elementId: 'categoryCarousel',
        itemCount: totalCategories,
        dataAttribute: 'category',
        inputId: 'storyCategory',
        onSelect: (categoryId) => {
            selectedCategory = categoryId;
        }
    });
    ```
  * Added a `setupCarouselKeyboardNavigation()` function to handle keyboard events for multiple carousels
  * Removed redundant carousel functions and global variables from the main JavaScript code
  * Updated event handlers to use the new class methods
- Result:
  * Improved code organization with carousel functionality isolated in its own module
  * Reduced duplication by using the same class for both carousels
  * Enhanced maintainability with changes to carousel behavior only needed in one place
  * Better encapsulation with carousel state managed within the class rather than using global variables
  * Cleaner HTML file with significantly reduced JavaScript code

## 2025-03-05: Added Code Complexity Analyzer Tool

### Created Development Tool for Identifying Refactoring Candidates
- Problem: Needed a way to identify files with excessive code size that might need refactoring
- Solution:
  * Created a new `tools/code_complexity_analyzer.py` utility script that:
    - Analyzes files in the repository to find those with the most lines
    - Counts total lines, non-blank lines, and code lines (excluding comments)
    - Supports filtering by file extension (e.g., `-e py js html`)
    - Allows sorting by different metrics (`-s total/non-blank/code`)
    - Provides a summary of total files and lines analyzed
  * Added comprehensive documentation with usage examples
  * Implemented comment pattern detection for Python, JavaScript, HTML, and CSS
  * Created a dedicated `tools/` directory for development utilities
- Result:
  * Identified that `app/templates/index.html` (1,251 lines) is the largest file in the project
  * Provided a reusable tool for ongoing code quality monitoring
  * Established a pattern for organizing development utilities separate from application code

## 2025-03-05: Fixed Loading Spinner Visibility for Chapter 1

### Fixed Loading Spinner Timing and Visibility Issues
- Problem: The loading spinner was disappearing too quickly for Chapter 1 but working fine for other chapters
- Root Cause:
  * The loader was being hidden immediately after content streaming but before image generation tasks for Chapter 1 were complete
  * CSS issues with the loader overlay were causing visibility problems
  * The WebSocket connection handler was hiding the loader too early in the process
- Solution:
  * Modified `stream_and_send_chapter()` in `websocket_service.py` to only hide the loader after all image tasks are complete:
    ```python
    # Only hide the loader after all image tasks are complete for Chapter 1
    # For other chapters, hide it immediately since there are no image tasks
    if not image_tasks:
        # No image tasks, hide loader immediately
        await websocket.send_json({"type": "hide_loader"})
    
    # If we have image tasks, wait for them to complete and send updates
    if image_tasks:
        # Process image tasks...
        
        # Hide loader after all image tasks are complete
        await websocket.send_json({"type": "hide_loader"})
    ```
  * Updated the WebSocket connection handler in `index.html` to not hide the loader immediately after connection:
    ```javascript
    this.connection.onopen = () => {
        console.log('WebSocket reconnected, restoring state...');
        // Don't hide loader here - wait for server to send hide_loader message
        this.reconnectAttempts = 0; // Reset counter on successful connection
        
        // Rest of the connection handling...
    };
    ```
  * Enhanced the `showLoader()` and `hideLoader()` functions with better error handling and logging
  * Fixed CSS issues in `loader.css` to ensure proper visibility of the loader overlay
  * Added `!important` to the hidden class to prevent style conflicts
- Result:
  * The loading spinner now remains visible during the entire image generation process for Chapter 1
  * The user experience is improved by accurately reflecting the loading state
  * The spinner is properly hidden after all content and images are loaded
  * Consistent behavior across all chapters with appropriate loading indicators

## 2025-03-05: Fixed Subprocess Python Interpreter Issue in Simulation Tests

### Fixed Python Interpreter Path in Subprocess Commands
- Problem: The `run_simulation_tests.py` script was failing to run the story simulation properly with a `ModuleNotFoundError: No module named 'websockets'` error, even though the package was installed in the virtual environment
- Root Cause:
  * When the script used commands like `["python", "tests/simulations/story_simulation.py"]` to create subprocesses, it wasn't necessarily using the same Python interpreter that was running the main script
  * This led to the subprocess potentially using a different Python interpreter that didn't have the required `websockets` package installed
  * The issue occurred specifically when running the script from within a virtual environment, where packages are installed locally to that environment
- Solution:
  * Modified `run_simulation_tests.py` to use `sys.executable` instead of "python" when creating subprocess commands
  * Changed the command for getting the run ID:
    ```python
    # Changed from:
    cmd = ["python", "tests/simulations/story_simulation.py", "--output-run-id"]
    # To:
    cmd = [sys.executable, "tests/simulations/story_simulation.py", "--output-run-id"]
    ```
  * Changed the command for running the actual simulation:
    ```python
    # Changed from:
    cmd = ["python", "tests/simulations/story_simulation.py"]
    # To:
    cmd = [sys.executable, "tests/simulations/story_simulation.py"]
    ```
  * This ensures that the subprocess uses the same Python interpreter that's running the main script, which has access to all the installed packages in the virtual environment
- Result:
  * The story simulation now runs correctly when executed through `run_simulation_tests.py`
  * The script properly generates chapters and allows making choices
  * All tests pass successfully when running the full test suite
  * The testing framework is now more reliable, ensuring consistent Python interpreter usage across all subprocess calls

## 2025-03-04: Mobile Font Size Controls Implementation

### Added Font Size Adjustment Feature for Mobile Users
- Problem: Mobile users needed a way to adjust font size for better readability
- Root Cause:
  * Text size that works well on desktop may be too small or large on mobile devices
  * Different mobile devices have varying screen sizes and resolutions
  * Users have different visual preferences and accessibility needs
- Solution:
  * Created a new `font-size-manager.js` file with a `FontSizeManager` class that:
    - Manages font size adjustments (from 80% to 200% of default size)
    - Saves user preferences to localStorage for persistence
    - Applies font size changes to both story content and choice buttons
    - Shows/hides controls on scroll (matching the chapter indicator behavior)
    - Only initializes on mobile devices (screen width ≤ 768px)
  * Updated the HTML structure in `index.html`:
    - Added font size controls (minus button, percentage display, plus button) in the header row
    - Removed the progress bar as it wasn't needed
    - Added proper ARIA labels for accessibility
  * Added CSS styles:
    - Mobile-only display for the font size controls
    - Styled buttons and percentage display to match the app's indigo theme
    - Added transitions for smooth show/hide behavior
    - Implemented disabled states for min/max font sizes
  * Updated the JavaScript:
    - Modified the `updateProgress` function to work without the progress bar
    - Added event dispatching for new chapter loads
    - Included the font-size-manager.js script
- Result:
  * Mobile users can now easily adjust text size for better readability
  * Font size preferences persist between sessions
  * Controls are only visible on mobile devices
  * Controls match the app's visual design using the indigo theme
  * Controls have the same scroll behavior as the chapter indicator

## 2025-03-04: Debug Toggle Removal

### Removed Debug Toggle Button from User Interface
- Problem: Debug toggle button was visible to users on both desktop and mobile
- Root Cause:
  * The debug toggle button was added during development for testing purposes
  * It was never hidden from the production UI
  * The button allowed users to see internal debugging information
- Solution:
  * Removed the "Toggle Debug Info" button from the UI in `index.html`
  * Kept the debug info div in the HTML but hidden by default
  * Added a comment explaining how developers can still access it via the console:
    `document.getElementById('debugInfo').style.display = 'block';`
- Result:
  * Cleaner user interface without developer tools visible to end users
  * Debug functionality still available to developers when needed
  * Improved user experience by removing non-essential UI elements

## 2025-03-04: Optimized Image Generation Prompts

### Streamlined Prompt Structure for More Consistent Images
- Problem: Image generation prompts were bloated with redundant information, causing inconsistent results
- Root Cause:
  * The prompt included multiple layers of descriptive text that sometimes conflicted with each other
  * Complex extraction logic with multiple approaches to extract agency details led to inconsistent results
  * Redundant information from choice text was being included even when visual details were already present
  * The prompt structure didn't prioritize the most important visual elements
- Solution:
  * Restructured the prompt format to focus on essential elements:
    ```
    Fantasy illustration of [Agency Name] in [Story Name], [Visual Details], with [adventure_state.selected_sensory_details["visuals"]], [Base Style]
    ```
  * Completely rewrote `enhance_prompt()` in `image_generation_service.py` to:
    - Extract the complete agency name with visual details up to the closing bracket
    - Include the story name from `adventure_state.metadata["non_random_elements"]["name"]`
    - Remove redundant descriptions that come after the dash
    - Add sensory details from the adventure state
    - Preserve the base style guidance
  * Added a helper method `_lookup_visual_details()` to find visual details when not present in the original prompt
  * Simplified agency option extraction in `websocket_service.py` to be more direct and reliable
- Result:
  * More consistent image generation with reduced token usage
  * Improved visual quality by focusing on essential elements
  * Better organization of prompt components in a logical order
  * Cleaner, more maintainable code with improved logging

## 2025-03-04: Fixed Outdated References to new_stories.yaml

### Updated Code to Use StoryLoader Consistently
- Problem: After refactoring story data into individual files, some parts of the codebase were still referencing the old `new_stories.yaml` file, causing errors
- Root Cause:
  * While `chapter_manager.py` was updated to use the new `StoryLoader` class during the story data refactoring, other files that directly loaded story data were missed
  * This caused errors when trying to load story data or generate chapters, as the application couldn't find the old monolithic YAML file
- Solution:
  * Updated `app/routers/web.py` to use the new `StoryLoader` class instead of directly loading from the old YAML file
  * Updated `app/services/websocket_service.py` to use the `StoryLoader` class in the `generate_chapter()` function
  * Updated `app/init_data.py` to use the `StoryLoader` class in the `load_story_data()` function
  * Updated `tests/simulations/story_simulation.py` to use the `StoryLoader` class in the `load_story_data()` function
- Result:
  * Fixed "Failed to load story data" error in the web interface
  * Fixed "Error generating chapter: [Errno 2] No such file or directory: 'app/data/new_stories.yaml'" error when starting an adventure
  * Ensured all parts of the application use the new story data structure consistently
  * Completed the story data refactoring process by updating all references to the old file

## 2025-03-04: Fixed Character Encoding Issue in Story Loader

### Fixed YAML File Loading with UTF-8 Encoding
- Problem: Character encoding error when loading YAML files: `'charmap' codec can't decode byte 0x9d in position 3643: character maps to <undefined>`
- Root Cause:
  * Files were being opened with the default system encoding (cp1252 on Windows)
  * One of the story files (specifically `jade_mountain.yaml`) contained a character (byte 0x9d) that couldn't be decoded using the default encoding
- Solution:
  * Modified the `load_all_stories()` method in `app/data/story_loader.py` to explicitly use UTF-8 encoding when opening files
  * Changed `with open(file_path, "r") as f:` to `with open(file_path, "r", encoding="utf-8") as f:`
- Result: Fixed character encoding issues when loading story files, ensuring proper handling of special characters in YAML content

## 2025-03-04: Story Data Organization Refactoring

### Improved Story Data Management with Individual Files
- Problem: All story categories were in a single YAML file, making maintenance difficult and increasing risk of syntax errors
- Solution:
  * Created a dedicated `app/data/stories/` directory to store individual story files
  * Split the monolithic `new_stories.yaml` into individual files for each story category:
    - `festival_of_lights_and_colors.yaml`
    - `circus_and_carnival_capers.yaml`
    - `enchanted_forest_tales.yaml`
    - `jade_mountain.yaml`
  * Implemented a dedicated `StoryLoader` class in `app/data/story_loader.py` with:
    - Caching for performance optimization
    - Error handling and logging
    - Methods for accessing individual stories and listing available categories
  * Updated `chapter_manager.py` to use the new loader while maintaining backward compatibility
  * Created proper test files in `tests/data/` directory:
    - `test_story_loader.py`: Tests story data loading functionality
    - `test_story_elements.py`: Tests random element selection
    - `test_chapter_manager.py`: Tests adventure state initialization
- Result: Improved maintainability, reduced risk of syntax errors, better scalability for adding new stories, and enhanced collaboration potential

## 2025-03-04: Dynamic Adventure Topic Reference in Exposition Phase

### Enhanced World Building Guidance with Adventure Topic Reference
- Problem: World building guidance in Exposition phase was generic and didn't reference the specific adventure topic selected by the user
- Solution:
  * Modified the BASE_PHASE_GUIDANCE dictionary in `prompt_templates.py` to add an {adventure_topic} placeholder in the "World Building" section of the "Exposition" phase guidance
  * Updated the `_get_phase_guidance()` function in `prompt_engineering.py` to replace the placeholder with the actual adventure topic name from `state.metadata["non_random_elements"]["name"]`
  * Added conditional logic to only apply this replacement for the "Exposition" phase
- Result: Exposition phase guidance now dynamically references the specific adventure topic (e.g., "Jade Mountain") selected by the user, creating a more tailored and immersive storytelling experience

## 2025-03-03: Renamed `setting_types` to `settings` and Removed `story_rules`

### Updated Data Model and Field Naming
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

## 2025-03-03: Removed Unused `character_archetypes` Field

### Removed Unnecessary `character_archetypes` Field from Story Categories
- Problem: The `character_archetypes` field in story categories wasn't being effectively utilized in the narrative generation
- Solution:
  * Removed the `character_archetypes` sections from each story category in `app/data/new_stories.yaml`
  * Modified `app/models/story.py` to remove `character_archetypes` from the required categories in the `validate_narrative_elements` validator
  * Updated `app/services/chapter_manager.py` to remove `character_archetypes` from the required categories in the `select_random_elements` function
  * Removed the `character_archetypes` line from the system prompt template in `app/services/llm/prompt_templates.py`
  * Removed the `character_archetypes` parameter from the system prompt formatting in `app/services/llm/prompt_engineering.py`
- Result: Simplified data model and prompt structure while maintaining narrative quality with other elements like settings, rules, themes, and sensory details

## 2025-03-03: Removed Unused `tone` Field

### Removed Unnecessary `tone` Field from Story Categories
- Problem: The `tone` field in story categories wasn't being passed into the LLM prompt used to generate chapters
- Solution:
  * Removed the `tone`
